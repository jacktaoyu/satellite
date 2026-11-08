import uuid

from sqlalchemy import Index, inspect, text

from database import db
from model.TaskModel import NewTaskModel, OldTaskModel, TaskResultModel


def _add_missing_columns(table_name, columns):
    inspector = inspect(db.engine)
    existing = {column['name'] for column in inspector.get_columns(table_name)}
    for column_name, column_type in columns.items():
        if column_name not in existing:
            db.session.execute(text(
                f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'
            ))


def _backfill_task_uuids(model):
    for task in model.query.filter(model.task_uuid.is_(None)).all():
        task.task_uuid = str(uuid.uuid4())


def _create_unique_index(table_name, index_name):
    indexes = {index['name'] for index in inspect(db.engine).get_indexes(table_name)}
    if index_name not in indexes:
        Index(index_name, db.metadata.tables[table_name].c.task_uuid, unique=True).create(db.engine)


def upgrade_task_schema():
    """非破坏性升级既有任务表；可重复执行，不删除或清空任何数据。"""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if 't_task_result' not in tables:
        TaskResultModel.__table__.create(db.engine)

    task_columns = {'task_uuid': 'VARCHAR(36)'}
    for table_name in ('t_new_task', 't_old_task'):
        if table_name in tables:
            _add_missing_columns(table_name, task_columns)
    if 't_old_task' in tables:
        _add_missing_columns('t_old_task', {
            'result_payload': 'TEXT',
            'result_received_at': 'DATETIME'
        })
    db.session.commit()

    _backfill_task_uuids(NewTaskModel)
    _backfill_task_uuids(OldTaskModel)
    db.session.commit()

    for table_name, index_name in (
            ('t_new_task', 'uq_new_task_uuid'),
            ('t_old_task', 'uq_old_task_uuid')):
        if table_name in tables:
            _create_unique_index(table_name, index_name)
