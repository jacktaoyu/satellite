import json
import os
import queue
import socket
import threading
import time
import uuid
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pytest
from flask import Flask

from client import SatelliteClient
from client_store import ClientResultStore
from database import db
from model.TaskModel import NewTaskModel, OldTaskModel, TaskResultModel
from Service.SatelliteNetworkService import SatelliteNetwork
from Service.TaskResultService import TaskResultService, TaskResultError
from Service.TaskService import Task
from Service.split import split_cycle_target_into_point_targets
from utils.task_schema import upgrade_task_schema


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI='sqlite://', SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()


def create_task_model(task_id=1):
    model = NewTaskModel(
        id=task_id,
        task_uuid=str(uuid.uuid4()),
        task_name='可靠性测试',
        priority=1,
        is_emergency=False,
        sensor_type='optical',
        task_type='点目标',
        resolution=0.5,
        start_time=datetime(2025, 6, 6),
        end_time=datetime(2025, 6, 6, 0, 1),
        target_location='[30.0, 120.0]',
        assigned_satellite_name='Sat_1_1',
        status='正在执行'
    )
    db.session.add(model)
    db.session.commit()
    return model


def result_for(model):
    return {
        'task_id': model.id,
        'task_uuid': model.task_uuid,
        'execution_duration_ms': 55,
        'result': '成功'
    }


def memory_task(model):
    return SimpleNamespace(task_id=model.id, task_uuid=model.task_uuid, parent_task_id=None)


def test_result_archive_is_transactional_and_idempotent(app):
    with app.app_context():
        model = create_task_model()
        task = memory_task(model)
        first = TaskResultService.process_result(task, result_for(model))
        second = TaskResultService.process_result(task, result_for(model))
        assert first['archived'] is True
        assert second['duplicate'] is True
        assert NewTaskModel.query.count() == 0
        assert OldTaskModel.query.count() == 1
        assert TaskResultModel.query.count() == 1
        archived = OldTaskModel.query.first()
        assert archived.task_uuid == model.task_uuid
        assert archived.status == 'Success'
        assert archived.result_received_at is not None


def test_mismatched_numeric_id_is_rejected(app):
    with app.app_context():
        model = create_task_model()
        result = result_for(model)
        result['task_id'] += 1
        with pytest.raises(TaskResultError, match='不匹配'):
            TaskResultService.process_result(memory_task(model), result)
        assert TaskResultModel.query.count() == 0
        assert NewTaskModel.query.count() == 1


def test_unknown_uuid_is_rejected(app):
    with app.app_context():
        with pytest.raises(TaskResultError, match='未知任务'):
            TaskResultService.process_result(None, {
                'task_id': 999, 'task_uuid': str(uuid.uuid4()), 'result': '成功'
            })


def test_schema_upgrade_is_repeatable_and_preserves_uuid(app):
    with app.app_context():
        model = create_task_model()
        original_uuid = model.task_uuid
        upgrade_task_schema()
        upgrade_task_schema()
        assert NewTaskModel.query.get(model.id).task_uuid == original_uuid
        assert 't_task_result' in db.engine.dialect.get_table_names(db.engine.connect())


def test_client_store_restores_unacked_result(tmp_path):
    path = tmp_path / 'client.sqlite3'
    result = {'task_id': 1, 'task_uuid': str(uuid.uuid4()), 'result': '成功'}
    store = ClientResultStore(str(path))
    assert store.enqueue_result(result) is True
    assert store.enqueue_result(result) is False
    store.close()
    restarted = ClientResultStore(str(path))
    assert restarted.pending_results() == [result]
    restarted.mark_ack(result['task_uuid'])
    assert restarted.pending_results() == []
    assert restarted.count('acked_results') == 1
    restarted.close()


def test_client_store_keeps_nack_history(tmp_path):
    store = ClientResultStore(str(tmp_path / 'client.sqlite3'))
    result = {'task_id': 2, 'task_uuid': str(uuid.uuid4()), 'result': '成功'}
    store.enqueue_result(result)
    store.mark_nack(result['task_uuid'], '未知任务')
    assert store.has_result(result['task_uuid']) is True
    assert store.enqueue_result(result) is False
    assert store.count('failed_results') == 1
    store.close()


def test_client_execution_uses_monotonic_wall_clock(tmp_path):
    client = SatelliteClient(store_path=str(tmp_path / 'client.sqlite3'))
    task = {'task_id': 1, 'task_uuid': str(uuid.uuid4()), 'execute_time': 0.06}
    client._execute_task(task)
    pending = client.store.pending_results()
    assert len(pending) == 1
    assert pending[0]['execution_duration_ms'] >= 45
    client.stop()


def test_client_stop_suppresses_fake_success(tmp_path):
    client = SatelliteClient(store_path=str(tmp_path / 'client.sqlite3'))
    worker = threading.Thread(target=client._execute_task, args=({
        'task_id': 1, 'task_uuid': str(uuid.uuid4()), 'execute_time': 0.2
    },))
    worker.start()
    time.sleep(0.02)
    client.stop()
    worker.join(timeout=1)
    assert client.result_queue.empty()
    reopened = ClientResultStore(str(tmp_path / 'client.sqlite3'))
    assert reopened.count('outbox') == 0
    reopened.close()


def test_send_failure_does_not_enter_running_queue():
    network = SatelliteNetwork.__new__(SatelliteNetwork)
    network.operation_center = SimpleNamespace(task_lock=nullcontext())
    network.new_tasks = []
    network.running_tasks = []
    network.client_sockets = [None]
    satellite = SimpleNamespace(client=0, is_available=True)
    network.satellites = {'Sat_1_1': satellite}
    now = datetime.now(timezone.utc)
    task = Task(1, '测试', [30, 120], None, now, now + timedelta(seconds=1))
    task.assigned_satellite = 'Sat_1_1'
    task.execution_time = 1
    network.new_tasks.append(task)
    network.check_execute_tasks(now.replace(tzinfo=None), 1000)
    assert network.running_tasks == []
    assert network.new_tasks == [task]


def test_disconnect_preserves_client_slot():
    network = SatelliteNetwork.__new__(SatelliteNetwork)
    network.running_tasks = []
    network.new_tasks = []
    network.satellites = {}
    network.operation_center = None
    network.is_connect = True
    client = SimpleNamespace(close=lambda: None)
    network.client_sockets = [client, None]
    network._handle_client_disconnect(client)
    assert network.client_sockets == [None, None]
    assert network.is_connect is False


def test_cycle_subtask_uuid_is_stable():
    now = datetime.now(timezone.utc)
    parent = Task(7, '周期', [30, 120], None, now + timedelta(hours=1), now,
                  task_type='周期观测', cycle_time=60)
    first = split_cycle_target_into_point_targets(parent)
    first_uuids = [task.task_uuid for task in first]
    parent.subtasks = []
    parent.subtask_ids = []
    second = split_cycle_target_into_point_targets(parent)
    assert [task.task_uuid for task in second] == first_uuids
    assert len(set(first_uuids)) == len(first_uuids)


def test_collect_results_supports_numpy_satellite_position(app):
    with app.app_context():
        model = create_task_model()
        task = memory_task(model)
        task.assigned_satellite = 'Sat_1_1'
        satellite = SimpleNamespace(
            position=np.array([7000.0, 0.0, 0.0]),
            running_task=model.id,
            status='RUNNING'
        )
        replies = []
        client_socket = SimpleNamespace(sendall=replies.append)
        network = SatelliteNetwork.__new__(SatelliteNetwork)
        network.app = app
        network.results_buffer = queue.Queue()
        network.results_buffer.put((client_socket, result_for(model)))
        network.running_tasks = [task]
        network.new_tasks = []
        network.net_tasks_buffer = {}
        network.satellites = {'Sat_1_1': satellite}

        network.collect_results()

        archived = OldTaskModel.query.filter_by(task_uuid=model.task_uuid).first()
        assert archived is not None
        assert archived.status == 'Success'
        assert archived.height == pytest.approx(629.0)
        assert NewTaskModel.query.count() == 0
        assert TaskResultModel.query.count() == 1
        assert network.running_tasks == []
        assert satellite.running_task is None
        assert satellite.status == 'FREE'
        assert json.loads(replies[0].decode('utf-8')) == {
            'type': 'ack', 'task_uuid': model.task_uuid
        }


def test_authentication_preserves_coalesced_result_bytes():
    network = SatelliteNetwork.__new__(SatelliteNetwork)
    network.auth_token = uuid.uuid4().hex
    network.results_buffer = queue.Queue()
    network.running_tasks = []
    network.new_tasks = []
    network.satellites = {}
    network.operation_center = None
    server_socket, client_socket = socket.socketpair()
    network.client_sockets = [server_socket]
    network.is_connect = True
    receiver = None
    try:
        result = {'task_id': 1, 'task_uuid': str(uuid.uuid4()), 'result': '成功'}
        client_socket.sendall(
            (json.dumps({'token': network.auth_token}) + '\n').encode('utf-8')
            + (json.dumps(result) + '\n').encode('utf-8')
        )
        remainder = network._verify_client_token(server_socket, ('127.0.0.1', 12345))
        assert remainder is not False
        assert json.loads(remainder.decode('utf-8').strip()) == result
        receiver = threading.Thread(
            target=network._receive_results, args=(server_socket, remainder), daemon=True
        )
        receiver.start()
        assert network.results_buffer.get(timeout=1) == (server_socket, result)
        client_socket.shutdown(socket.SHUT_RDWR)
        receiver.join(timeout=1)
        assert not receiver.is_alive()
    finally:
        server_socket.close()
        client_socket.close()
