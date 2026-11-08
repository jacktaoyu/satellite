import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from flask import Flask

from blueprint.Satellite import satellite_bp
from blueprint.Task import task_bp
from database import db
from extions import occ
from model.TaskModel import NewTaskModel, OldTaskModel
from Service.Greedy import GreedyScheduler
from utils.downlink_windows import normalize_downlink_windows


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI='sqlite://', SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    app.register_blueprint(task_bp)
    app.register_blueprint(satellite_bp)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        occ._instance = None


def add_new_task(task_id, name='普通任务', status='等待规划'):
    model = NewTaskModel(
        id=task_id,
        task_uuid=str(uuid.uuid4()),
        task_name=name,
        priority=1,
        is_emergency=False,
        sensor_type='optical',
        task_type='点目标',
        resolution=0.5,
        start_time=datetime(2025, 6, 6),
        end_time=datetime(2025, 6, 6, 1),
        target_location='[30.0, 120.0]',
        assigned_satellite_name='Sat_1_1',
        status=status
    )
    db.session.add(model)
    db.session.commit()
    return model


def test_cross_page_search_runs_before_pagination(app):
    with app.app_context():
        for task_id in range(1, 13):
            add_new_task(task_id)
        target = add_new_task(13, '跨页目标')
        client = app.test_client()
        response = client.post('/tasks/getNewTasks', json={
            'page': 1, 'page_size': 10, 'search': '跨页目标'
        })
        data = response.get_json()['data']
        assert response.status_code == 200
        assert data['total'] == 1
        assert data['items'][0]['id'] == target.id
        assert data['items'][0]['task_uuid'] == target.task_uuid


def test_numeric_id_search_and_page_fallback(app):
    with app.app_context():
        for task_id in range(1, 12):
            add_new_task(task_id)
        client = app.test_client()
        found = client.post('/tasks/getNewTasks', json={'search': '11'}).get_json()['data']
        assert found['total'] == 1
        assert found['items'][0]['id'] == 11
        fallback = client.post('/tasks/getNewTasks', json={
            'page': 99, 'page_size': 5
        }).get_json()['data']
        assert fallback['current_page'] == 3
        assert len(fallback['items']) == 1


def test_unified_stats_include_new_and_old_statuses(app):
    with app.app_context():
        add_new_task(1, status='正在执行')
        add_new_task(2, status='等待执行')
        db.session.add(OldTaskModel(
            id=1, task_uuid=str(uuid.uuid4()), task_name='已完成', priority=1,
            is_emergency=False, sensor_type='optical', task_type='点目标',
            target_location='[30.0, 120.0]', status='Success', result_payload='{"result":"成功"}',
            result_received_at=datetime.utcnow()
        ))
        db.session.commit()
        response = app.test_client().get('/tasks/getTaskStats')
        data = response.get_json()['data']
        assert data['total'] == 3
        assert data['running'] == 1
        assert data['waiting'] == 1
        assert data['success'] == 1


def test_history_returns_uuid_result_and_times(app):
    with app.app_context():
        received_at = datetime.utcnow()
        old = OldTaskModel(
            id=8, task_uuid=str(uuid.uuid4()), task_name='历史结果', priority=1,
            is_emergency=False, sensor_type='optical', task_type='点目标',
            start_time=datetime(2025, 6, 6), end_time=datetime(2025, 6, 6, 0, 1),
            target_location='[30.0, 120.0]', assigned_satellite_name='Sat_1_1',
            status='Success', result_payload='{"execution_duration_ms":42}',
            result_received_at=received_at
        )
        db.session.add(old)
        db.session.commit()
        data = app.test_client().post('/tasks/getOldTasks', json={}).get_json()['data']['items'][0]
        assert data['task_uuid'] == old.task_uuid
        assert data['satellite_name'] == 'Sat_1_1'
        assert data['result_payload'] == '{"execution_duration_ms":42}'
        assert data['result_received_at'] is not None


def test_satellite_list_returns_real_battery_capacity(app):
    satellite = SimpleNamespace(
        sat_id=1, sat_name='Sat_1_1', storage=10, battery=2500,
        battery_capacity=5000, resolution_capability=0.5,
        alias='第1轨道第1卫星', star_payload='optical', is_available=True
    )
    occ.set_instance(SimpleNamespace(satellite_network=SimpleNamespace(
        satellites={'Sat_1_1': satellite}
    )))
    response = app.test_client().post('/satellites/getAllSatellites', json={})
    item = response.get_json()[0]
    assert item['battery'] == 2500
    assert item['maxBattery'] == 5000


def test_downlink_window_normalization_supports_all_shapes():
    start = datetime(2025, 6, 6)
    end = start + timedelta(minutes=5)
    assert normalize_downlink_windows([start, end]) == [(start, end)]
    assert normalize_downlink_windows((start, end)) == [(start, end)]
    assert normalize_downlink_windows({'start': start, 'end': end}) == [(start, end)]
    assert normalize_downlink_windows({'w1': {'start_time': start, 'end_time': end}}) == [(start, end)]
    assert normalize_downlink_windows({'bad': {'value': 1}}) == []


def test_greedy_accepts_list_and_mapped_dict_windows():
    start = datetime(2025, 6, 6)
    end = start + timedelta(minutes=5)
    scheduler = GreedyScheduler.__new__(GreedyScheduler)
    for windows in ([[start, end]], {'w1': {'start_time': start, 'end_time': end}}):
        satellite = SimpleNamespace(sat_id=1, downlink_windows=windows, downlink_rate=1024)
        volume, tasks = scheduler._process_downlink_between_tasks_with_tasks(
            satellite, start, end, 1.0, [7], {7: 1.0}
        )
        assert volume == 1.0
        assert tasks == [7]


def test_single_task_preserves_custom_name_and_supports_blank_fallback():
    from queue import Queue
    from Service.ControlleService import OperationsControlCenter

    def create_controller():
        controller = OperationsControlCenter.__new__(OperationsControlCenter)
        controller.now_time = datetime(2025, 6, 6, 12, 0, 0)
        controller.appointment_tasks = []
        controller.tasks_buffer = {}
        controller.task_queue = Queue()
        controller._add_task = lambda task, *args: 42
        return controller

    data = {
        'task_name': '用户命名任务', 'type': '点目标', 'priority': 1,
        'is_urgent': '否', 'payload': '光学', 'resolution': 0.5,
        'timeRanges': [''], 'cycle': '60', 'longitude': 116.4,
        'latitude': 39.9, 'angle': 0, 'cloud_thickness': 0,
        'cluster_name': '', 'appoint_time': '', 'coordinates': ['39.9,116.4'],
    }
    task = create_controller().generate_single_task(data)
    assert task.task_name == '用户命名任务'
    assert task.task_id == 42
    assert task.task_uuid

    fallback = dict(data, task_name='   ')
    task = create_controller().generate_single_task(fallback)
    assert task.task_name.startswith('点目标')
    assert len(task.task_name) == len('点目标') + 6


def test_case_result_empty_archive_is_successful_empty_state(app):
    client = app.test_client()
    for case_type in ('point', 'area', 'ocean'):
        response = client.get(f'/tasks/caseResult/{case_type}')
        assert response.status_code == 200
        assert response.get_json()['status'] == 'success'
        assert response.get_json()['data'] is None
    assert client.get('/tasks/caseResult/unknown').status_code == 400


def test_production_cesium_assets_are_public_but_api_stays_protected(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    monkeypatch.setenv('JWT_SECRET', uuid.uuid4().hex)
    import app as production_app

    client = production_app.app.test_client()
    with production_app.app.test_request_context('/cesium/Workers/transferTypedArrayTest.js'):
        assert production_app.global_auth_check() is None
    with production_app.app.test_request_context('/vite.svg'):
        assert production_app.global_auth_check() is None
    assert client.get('/vite.svg').status_code == 200
    response = client.get('/tasks/getTaskStats')
    assert response.status_code == 401
