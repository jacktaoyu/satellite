# -*- coding: utf-8 -*-
"""真实 OCC—双客户端闭环验收；仅使用独立数据库和运行时随机凭据。"""
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from client import SatelliteClient


BACKEND_DIR = Path(__file__).resolve().parent
RUN_ID = datetime.now().strftime('%Y%m%d_%H%M%S') + f'_{os.getpid()}'


def request_json(base_url, path, method='GET', payload=None, token=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Ac-Token'] = token
    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode('utf-8')
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


def wait_until(check, timeout, interval=1.0, description='条件'):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except Exception as error:
            last_error = error
        time.sleep(interval)
    raise TimeoutError(f'等待{description}超时；最后错误：{last_error}')


def receive_reply(client_socket):
    buffer = b''
    while not buffer.endswith(b'\n'):
        chunk = client_socket.recv(65536)
        if not chunk:
            raise ConnectionError('服务端在结果确认前关闭连接')
        buffer += chunk
    return json.loads(buffer.decode('utf-8'))


def send_raw_result(result, token):
    with socket.create_connection(('127.0.0.1', 9999), timeout=10) as client_socket:
        client_socket.settimeout(20)
        client_socket.sendall((json.dumps({'token': token}) + '\n').encode('utf-8'))
        client_socket.sendall((json.dumps(result, ensure_ascii=False) + '\n').encode('utf-8'))
        return receive_reply(client_socket)


def main():
    base_dir = BACKEND_DIR.resolve()
    database_path = base_dir / f'acceptance_occ_{RUN_ID}.sqlite3'
    server_log_path = base_dir / f'acceptance_occ_{RUN_ID}.log'
    api_port = 5100 + (os.getpid() % 300)
    base_url = f'http://127.0.0.1:{api_port}'
    socket_token = secrets.token_urlsafe(32)
    admin_password = secrets.token_urlsafe(16)
    environment = os.environ.copy()
    environment.update({
        'DATABASE_URL': f'sqlite:///{database_path}',
        'SOCKET_AUTH_TOKEN': socket_token,
        'ADMIN_INIT_PASSWORD': admin_password,
        'PORT': str(api_port),
        'PYTHONPATH': str(base_dir.parent / '.runtime-deps') + os.pathsep + str(base_dir),
        'PYTHONUNBUFFERED': '1',
    })
    os.environ['SOCKET_AUTH_TOKEN'] = socket_token
    clients = []
    server_log = server_log_path.open('w', encoding='utf-8')
    server = subprocess.Popen(
        [sys.executable, 'app.py'], cwd=base_dir, env=environment,
        stdout=server_log, stderr=subprocess.STDOUT,
    )
    task_uuid = None
    try:
        health = wait_until(
            lambda: request_json(base_url, '/health'), 120,
            description='后端与健康检查就绪',
        )
        if not health.get('database') or not health.get('occ'):
            raise AssertionError(f'OCC 或数据库未就绪：{health}')

        login = request_json(base_url, '/login/', 'POST', {
            'username': 'admin', 'password': admin_password, 'value': '1',
        })
        token = login['data']['token']

        for index in range(2):
            store_path = base_dir / f'acceptance_client_{RUN_ID}_{index}.sqlite3'
            client = SatelliteClient(
                server_ip='127.0.0.1', server_port=9999,
                store_path=str(store_path), reconnect_interval=1.0, ack_timeout=5.0,
            )
            clients.append(client)
            threading.Thread(target=client.start, daemon=True).start()

        def network_ready():
            current = request_json(base_url, '/health')
            if current.get('networkReady') and current.get('clients') == 2:
                return current
            return None

        ready = wait_until(network_ready, 180, description='双客户端接入与卫星网络初始化')

        task_name = f'真实闭环验收_{RUN_ID}'
        created = request_json(base_url, '/tasks/addSingleTask', 'POST', {
            'task_name': task_name,
            'priority': 9,
            'is_urgent': '是',
            'type': '点目标',
            'payload': 'optical',
            'resolution': 1.0,
            'timeRanges': [''],
            'cycle': '60',
            'cloud_thickness': '0',
            'cluster_name': '',
            'appoint_time': '',
            'coordinates': ['30, 120'],
        }, token)
        if created.get('result') != 'ok' or not created.get('taskUuid'):
            raise AssertionError(f'任务创建失败：{created}')
        task_id = created['taskId']
        task_uuid = created['taskUuid']
        print(f'任务已创建：id={task_id}, uuid={task_uuid}')

        saw_waiting = False
        saw_running = False
        accelerated = False
        deadline = time.monotonic() + 360
        archived = None
        while time.monotonic() < deadline:
            new_page = request_json(base_url, '/tasks/getNewTasks', 'POST', {
                'search': task_uuid, 'page': 1, 'page_size': 10,
            }, token)
            new_items = new_page['data']['items']
            if new_items:
                status = new_items[0]['status']
                saw_waiting = saw_waiting or status in ('等待规划', '等待执行')
                saw_running = saw_running or status == '正在执行'
                print(f'任务状态：{status}；分配卫星：{new_items[0].get("satellite_name")}')
                if status == '等待执行' and not accelerated:
                    request_json(
                        base_url,
                        '/satellites/getCurrentMultiplierAndTime?multiplier=1000',
                        'POST', token=token,
                    )
                    accelerated = True
            else:
                old_page = request_json(base_url, '/tasks/getOldTasks', 'POST', {
                    'search': task_uuid, 'page': 1, 'page_size': 10,
                }, token)
                if old_page['data']['items']:
                    archived = old_page['data']['items'][0]
                    break
            time.sleep(0.5)
        if archived is None:
            raise TimeoutError('任务未在 360 秒内归档')
        if not saw_waiting or not saw_running:
            raise AssertionError(f'未完整观察到任务生命周期：waiting={saw_waiting}, running={saw_running}')
        if archived['task_uuid'] != task_uuid or archived['status'] != 'Success':
            raise AssertionError(f'历史任务 UUID 或状态错误：{archived}')
        result_payload = json.loads(archived['result_payload'])
        if result_payload['execution_duration_ms'] <= 0:
            raise AssertionError(f'真实执行耗时无效：{result_payload}')

        stats = request_json(base_url, '/tasks/getTaskStats', token=token)['data']
        if stats['success'] != 1 or stats['completed'] != 1:
            raise AssertionError(f'统一统计错误：{stats}')

        for client in clients:
            client.stop()
        time.sleep(2)
        ack_total = 0
        outbox_total = 0
        for index in range(2):
            store_path = base_dir / f'acceptance_client_{RUN_ID}_{index}.sqlite3'
            with sqlite3.connect(store_path) as connection:
                ack_total += connection.execute(
                    'SELECT COUNT(*) FROM acked_results WHERE task_uuid = ?', (task_uuid,),
                ).fetchone()[0]
                outbox_total += connection.execute(
                    'SELECT COUNT(*) FROM outbox WHERE task_uuid = ?', (task_uuid,),
                ).fetchone()[0]
        if ack_total != 1 or outbox_total != 0:
            raise AssertionError(f'客户端 ACK 或发件箱状态错误：ack={ack_total}, outbox={outbox_total}')

        duplicate_reply = send_raw_result(result_payload, socket_token)
        unknown_payload = dict(result_payload, task_uuid=secrets.token_hex(16))
        unknown_reply = send_raw_result(unknown_payload, socket_token)
        if duplicate_reply.get('type') != 'ack' or unknown_reply.get('type') != 'nack':
            raise AssertionError(f'异常回传响应错误：{duplicate_reply}, {unknown_reply}')

        with sqlite3.connect(database_path) as connection:
            receipt_count = connection.execute(
                'SELECT COUNT(*) FROM t_task_result WHERE task_uuid = ?', (task_uuid,),
            ).fetchone()[0]
            old_count = connection.execute(
                'SELECT COUNT(*) FROM t_old_task WHERE task_uuid = ?', (task_uuid,),
            ).fetchone()[0]
        if receipt_count != 1 or old_count != 1:
            raise AssertionError(f'重复回传未幂等：receipt={receipt_count}, old={old_count}')

        print(json.dumps({
            'result': 'ok',
            'taskId': task_id,
            'taskUuid': task_uuid,
            'satellite': archived['satellite_name'],
            'status': archived['status'],
            'executionDurationMs': result_payload['execution_duration_ms'],
            'ack': True,
            'duplicateAck': duplicate_reply['type'],
            'unknownNack': unknown_reply['type'],
            'receiptCount': receipt_count,
            'oldTaskCount': old_count,
            'database': str(database_path),
            'serverLog': str(server_log_path),
        }, ensure_ascii=False, indent=2))
    finally:
        for client in clients:
            try:
                client.stop()
            except Exception:
                pass
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        server_log.close()
        if task_uuid:
            print(f'验收数据库与日志保留在：{database_path}、{server_log_path}')


if __name__ == '__main__':
    main()
