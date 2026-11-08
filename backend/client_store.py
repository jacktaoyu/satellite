import json
import os
import sqlite3
import threading
from datetime import datetime


class ClientResultStore:
    """SQLite 持久发件箱；ACK/NACK 均保留历史并跨表去重。"""

    def __init__(self, path):
        self.path = path
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        with self.connection:
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS outbox (
                    task_uuid TEXT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS acked_results (
                    task_uuid TEXT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    acked_at TEXT NOT NULL
                )
            ''')
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS failed_results (
                    task_uuid TEXT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    failed_at TEXT NOT NULL,
                    reason TEXT
                )
            ''')
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS client_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

    def close(self):
        with self.lock:
            self.connection.close()

    def has_result(self, task_uuid):
        with self.lock:
            for table in ('outbox', 'acked_results', 'failed_results'):
                row = self.connection.execute(
                    f'SELECT 1 FROM {table} WHERE task_uuid = ?', (task_uuid,)
                ).fetchone()
                if row:
                    return True
        return False

    def enqueue_result(self, result):
        task_uuid = result['task_uuid']
        payload = json.dumps(result, ensure_ascii=False)
        with self.lock, self.connection:
            if self.has_result(task_uuid):
                return False
            self.connection.execute(
                'INSERT INTO outbox(task_uuid, task_id, payload, created_at) VALUES (?, ?, ?, ?)',
                (task_uuid, int(result['task_id']), payload, datetime.utcnow().isoformat())
            )
        return True

    def pending_results(self):
        with self.lock:
            rows = self.connection.execute(
                'SELECT payload FROM outbox ORDER BY created_at, task_uuid'
            ).fetchall()
        return [json.loads(row['payload']) for row in rows]

    def _move_result(self, table, task_uuid, timestamp_column, reason=None):
        now = datetime.utcnow().isoformat()
        with self.lock, self.connection:
            row = self.connection.execute(
                'SELECT * FROM outbox WHERE task_uuid = ?', (task_uuid,)
            ).fetchone()
            if row is None:
                return False
            if table == 'failed_results':
                self.connection.execute(f'''
                    INSERT OR REPLACE INTO {table}
                    (task_uuid, task_id, payload, created_at, {timestamp_column}, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (row['task_uuid'], row['task_id'], row['payload'], row['created_at'], now, reason))
            else:
                self.connection.execute(f'''
                    INSERT OR REPLACE INTO {table}
                    (task_uuid, task_id, payload, created_at, {timestamp_column})
                    VALUES (?, ?, ?, ?, ?)
                ''', (row['task_uuid'], row['task_id'], row['payload'], row['created_at'], now))
            self.connection.execute('DELETE FROM outbox WHERE task_uuid = ?', (task_uuid,))
        return True

    def mark_ack(self, task_uuid):
        return self._move_result('acked_results', task_uuid, 'acked_at')

    def mark_nack(self, task_uuid, reason):
        return self._move_result('failed_results', task_uuid, 'failed_at', reason)

    def count(self, table):
        if table not in ('outbox', 'acked_results', 'failed_results', 'client_meta'):
            raise ValueError('未知表名')
        with self.lock:
            return self.connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
