# -*- coding: utf-8 -*-
"""录制完整桌面功能巡演与真实 OCC—客户端闭环，不添加字幕或说明贴片。"""
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from record_full_flow import (
    BACKEND_DIR, PROJECT_DIR, WORK_DIR, OUTPUT_DIR,
    SatelliteClient, create_task, login, request_json, task_page, wait_for_satellite_imagery, wait_until,
)

RUN_ID = datetime.now().strftime('%Y%m%d_%H%M%S') + f'_{os.getpid()}'
KIND = 'complete_desktop_smooth'
EVIDENCE_DIR = WORK_DIR / 'evidence' / f'{KIND}_{RUN_ID}'
VIDEO_DIR = WORK_DIR / 'videos' / KIND
CAPTURE_LOG = WORK_DIR / f'{KIND}_{RUN_ID}.log'
for directory in (EVIDENCE_DIR, VIDEO_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)


class Tee:
    """同时保留终端输出和客户端 ACK／重发证据，不记录登录凭据。"""
    def __init__(self, stream, log_path):
        self.stream = stream
        self.log = log_path.open('a', encoding='utf-8')

    def write(self, text):
        self.stream.write(text)
        self.log.write(text)
        return len(text)

    def flush(self):
        self.stream.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def hold(page, milliseconds=2500):
    page.wait_for_timeout(milliseconds)


def capture(page, name, sections):
    path = EVIDENCE_DIR / f'{KIND}_{name}.png'
    page.screenshot(path=str(path), full_page=True)
    sections.append({'name': name, 'time': datetime.now().isoformat(timespec='seconds')})
    print(f'已录制功能段：{name}', flush=True)


def open_menu(page, label, path, ready_text=None, ready_selector=None):
    item = page.locator('.el-menu-item:visible').filter(has_text=label).first
    item.wait_for(state='visible', timeout=15000)
    item.click()
    page.wait_for_url(f'**{path}', timeout=30000)
    if ready_selector:
        page.locator(ready_selector).first.wait_for(state='visible', timeout=60000)
    if ready_text:
        page.get_by_text(ready_text, exact=True).first.wait_for(state='visible', timeout=60000)
    hold(page, 2500)


def open_task_subpage(page, label, path, ready_selector):
    item = page.locator('.el-menu-item').filter(has_text=label).first
    if not item.is_visible():
        page.locator('.el-sub-menu__title:visible').filter(has_text='任务管理').click()
    item.wait_for(state='visible', timeout=10000)
    item.click()
    page.wait_for_url(f'**{path}', timeout=30000)
    page.locator(ready_selector).first.wait_for(state='visible', timeout=30000)
    hold(page, 2500)


def open_tasks(page):
    open_task_subpage(page, '任务属性', '/satellite/renwu/shuxing', '.task-manage')


def open_network(page):
    open_menu(page, '卫星网络', '/satellite/satellite_network', ready_selector='.task-list')


def close_dialog(page, dialog):
    if dialog.locator('.el-dialog__headerbtn').count():
        dialog.locator('.el-dialog__headerbtn').click()
    else:
        page.keyboard.press('Escape')
    dialog.wait_for(state='hidden', timeout=15000)


def show_portal_and_register(page, base_url, sections):
    page.goto(base_url + '/portal', wait_until='domcontentloaded', timeout=60000)
    page.locator('.portal-container').wait_for(state='visible', timeout=60000)
    hold(page, 6500)
    capture(page, '01_portal', sections)
    page.locator('.nav-enter-btn').click()
    page.locator('.login-form').wait_for(state='visible', timeout=20000)
    hold(page, 3000)
    capture(page, '02_login_entry', sections)
    page.get_by_text('立即注册', exact=True).click()
    page.wait_for_url('**/register', timeout=20000)
    page.locator('.register-form .submit-btn').wait_for(state='visible')
    hold(page, 3500)
    capture(page, '03_register', sections)
    page.get_by_text('返回登录', exact=True).click()
    page.wait_for_url('**/login', timeout=20000)


def show_network(page, sections):
    first_sat = page.locator('.sat-item .sat-name').first
    first_sat.wait_for(state='visible', timeout=120000)
    satellite_name = first_sat.inner_text().strip()
    capture(page, '04_satellite_network', sections)
    search = page.get_by_placeholder('搜索卫星名称 / 载荷类型…', exact=True)
    search.press_sequentially(satellite_name, delay=60)
    hold(page, 1800)
    page.locator('.sat-item').first.click()
    page.locator('.right-panel .detail-name').wait_for(state='visible', timeout=20000)
    hold(page, 3500)
    capture(page, '05_satellite_focus_and_subtrack', sections)
    page.locator('.sat-search-clear').click()
    for label in ('全部轨迹', '全部视锥体', '通信链路'):
        row = page.locator('.quick-actions .detail-row').filter(has_text=label)
        row.locator('label.hud-switch').click()
        hold(page, 1200)
        row.locator('label.hud-switch').click()
        hold(page, 1200)
    capture(page, '06_network_layers_and_links', sections)
    return satellite_name


def show_system_settings(page, sections):
    open_menu(page, '系统设置', '/satellite/system_settings', ready_text='时间和参数设置')
    capture(page, '07_system_settings', sections)
    page.get_by_title('刷新列表', exact=True).click()
    hold(page, 2500)
    select = page.locator('.sat-select-wrapper .el-select')
    select.scroll_into_view_if_needed()
    select.click()
    option = page.locator('.el-select-dropdown__item:visible').first
    option.wait_for(state='visible', timeout=15000)
    option.click()
    page.locator('.satellite-form-wrapper').wait_for(state='visible', timeout=20000)
    hold(page, 3000)
    capture(page, '08_single_satellite_parameters', sections)
    page.get_by_role('button', name='按载荷批量设置', exact=True).click()
    page.wait_for_url('**/satellite/network_parameters', timeout=20000)
    page.locator('.params-form-card').wait_for(state='visible', timeout=20000)
    hold(page, 2500)
    capture(page, '09_payload_parameters_optical', sections)
    for label, name in (('SAR', '10_payload_parameters_sar'), ('红外', '11_payload_parameters_infrared')):
        page.locator('.sensor-card').filter(has_text=label).click()
        hold(page, 2200)
        capture(page, name, sections)


def show_satellite_management(page, satellite_name, sections):
    open_menu(page, '卫星管理', '/satellite/weixing', ready_selector='.satellite-manage')
    page.locator('.el-table__body-wrapper tbody tr').first.wait_for(state='visible', timeout=30000)
    search = page.get_by_placeholder('请输入卫星名称搜索', exact=True)
    search.press_sequentially(satellite_name, delay=60)
    search.press('Enter')
    hold(page, 2200)
    capture(page, '12_satellite_management_search', sections)
    row = page.locator('.el-table__body-wrapper tbody tr').filter(has_text=satellite_name).first
    row.get_by_role('button', name='详情', exact=True).click()
    page.wait_for_url('**/satellite/Weixing/info/*', timeout=20000)
    page.locator('.satellite-detail .satellite-name').wait_for(state='visible', timeout=30000)
    hold(page, 3000)
    capture(page, '13_satellite_detail_realtime', sections)
    payload = page.get_by_text('载荷参数', exact=True).last
    payload.scroll_into_view_if_needed()
    hold(page, 2500)
    capture(page, '14_satellite_detail_payload', sections)
    page.get_by_role('button', name='返回', exact=True).click()
    page.wait_for_url('**/satellite/weixing', timeout=20000)
    page.locator('.satellite-manage .search-card').get_by_role('button', name='重置', exact=True).click()
    hold(page, 2200)
    row = page.locator('.el-table__body-wrapper tbody tr').first
    row.get_by_role('button', name='编辑', exact=True).click()
    dialog = page.locator('.el-dialog:visible').filter(has_text='编辑卫星参数').last
    dialog.wait_for(state='visible', timeout=15000)
    hold(page, 3000)
    capture(page, '15_satellite_edit_cancel', sections)
    dialog.get_by_role('button', name='取消', exact=True).click()
    dialog.wait_for(state='hidden', timeout=15000)


def show_task_settings(page, sections):
    open_task_subpage(page, '任务设置', '/satellite/renwu/shezhi', '.task-settings')
    capture(page, '16_task_import_and_cases', sections)
    page.get_by_text('导入说明', exact=True).scroll_into_view_if_needed()
    hold(page, 2500)


def show_clusters(page, sections):
    open_menu(page, '星簇管理', '/satellite/xingcu', ready_selector='.cluster-manage')
    row = page.locator('.el-table__body-wrapper tbody tr').first
    row.wait_for(state='visible', timeout=30000)
    capture(page, '17_cluster_management', sections)
    row.get_by_role('button', name='详情', exact=True).click()
    dialog = page.locator('.el-dialog:visible').filter(has_text='星簇详情').last
    dialog.wait_for(state='visible', timeout=15000)
    hold(page, 3500)
    capture(page, '18_cluster_detail', sections)
    dialog.get_by_role('button', name='关闭', exact=True).click()
    dialog.wait_for(state='hidden', timeout=15000)


def show_ground_stations(page, sections):
    open_menu(page, '地面站', '/satellite/ground_station', ready_selector='.gs-page')
    row = page.locator('.el-table__body-wrapper tbody tr').first
    row.wait_for(state='visible', timeout=30000)
    row.locator('.el-table__expand-icon').click()
    page.locator('.expand-content').first.wait_for(state='visible', timeout=15000)
    hold(page, 3000)
    capture(page, '19_ground_station_links', sections)


def show_cases(page, sections):
    open_menu(page, '示范用例', '/satellite/yongli', ready_selector='.case-demo')
    capture(page, '20_demo_cases', sections)
    for index, name in enumerate(('21_case_point_detail', '22_case_area_detail', '23_case_ocean_detail')):
        page.evaluate('performance.clearResourceTimings()')
        page.get_by_role('button', name='查看详情', exact=True).nth(index).click()
        dialog = page.locator('.el-dialog:visible').filter(has_text='用例详情').last
        dialog.wait_for(state='visible', timeout=20000)
        case_map = dialog.locator('.case-map')
        case_map.wait_for(state='visible', timeout=30000)
        case_map.locator('canvas').wait_for(state='visible', timeout=30000)
        wait_for_satellite_imagery(case_map)
        hold(page, 6000)
        capture(page, name, sections)
        if dialog.get_by_text('最近执行结果（归档数据）', exact=True).count():
            dialog.get_by_text('最近执行结果（归档数据）', exact=True).scroll_into_view_if_needed()
            hold(page, 3500)
        page.get_by_text('执行流程', exact=True).last.scroll_into_view_if_needed()
        hold(page, 2000)
        close_dialog(page, dialog)


def show_alerts_and_replay(page, satellite_name, sections):
    open_menu(page, '告警中心', '/satellite/alerts', ready_selector='.alert-center')
    capture(page, '24_alert_center', sections)
    page.locator('.filter-bar').get_by_text('警告', exact=True).click()
    hold(page, 1800)
    page.locator('.filter-bar').get_by_text('全部级别', exact=True).click()
    print('告警筛选完成，准备进入态势回放', flush=True)
    open_menu(page, '态势回放', '/satellite/replay', ready_selector='.replay-page')
    print('态势回放页面已打开', flush=True)
    play = page.locator('.cb-actions button').first
    if play.is_enabled() and play.inner_text().strip() == '播放':
        play.click()
        hold(page, 3500)
        if play.inner_text().strip() == '暂停':
            play.click()
            print('态势回放播放与暂停完成', flush=True)
        else:
            print('态势回放已自动播放至末帧', flush=True)
    search = page.get_by_placeholder('搜索卫星名称…', exact=True)
    if search.count():
        search.fill(satellite_name)
        hold(page, 1800)
    capture(page, '25_state_replay', sections)


def find_ack(clients, task_uuid):
    for index, client in enumerate(clients):
        with client.store.lock:
            row = client.store.connection.execute(
                'SELECT task_uuid, task_id, acked_at FROM acked_results WHERE task_uuid = ?',
                (task_uuid,),
            ).fetchone()
            pending = client.store.connection.execute(
                'SELECT 1 FROM outbox WHERE task_uuid = ?', (task_uuid,),
            ).fetchone()
        if row and not pending:
            return {
                'confirmed': True, 'clientIndex': index,
                'storePath': str(client.store.path),
                'taskUuid': row['task_uuid'], 'taskId': row['task_id'],
                'ackedAt': row['acked_at'],
            }
    return None


def run_task_closed_loop(page, base_url, token, task_name, clients, sections):
    created = wait_until(
        lambda: task_page(base_url, token, task_name), 30, interval=0.1,
        description='完整巡演任务创建入库',
    )
    task_uuid = created.get('task_uuid') or created.get('taskUuid')
    if not task_uuid:
        raise AssertionError(f'新任务缺少稳定业务 UUID：{created}')
    created_status = created.get('status')
    if created_status != '等待规划':
        raise AssertionError(f'提交后未捕获自动规划初始状态：{created_status}')

    search = page.get_by_placeholder('任务名称 / 数字ID / 业务UUID', exact=True)
    row = page.locator('.el-table__body-wrapper tbody tr').first
    row.wait_for(state='visible', timeout=15000)
    capture(page, '26_task_created', sections)
    row.get_by_role('button', name='详情', exact=True).click()
    dialog = page.locator('.el-dialog:visible').filter(has_text='任务详情').last
    dialog.wait_for(state='visible', timeout=15000)
    dialog.get_by_text('等待规划', exact=True).wait_for(state='visible', timeout=5000)
    hold(page, 1800)
    capture(page, '27_task_planning', sections)
    close_dialog(page, dialog)

    planned = wait_until(
        lambda: (
            lambda current: current if current and current.get('status') in ('等待执行', '正在执行') else None
        )(task_page(base_url, token, task_name)),
        45, interval=0.2, description='自动规划完成并分配卫星',
    )
    assigned_satellite = planned.get('assignedSatelliteName') or planned.get('satellite_name')
    if not assigned_satellite:
        raise AssertionError(f'自动规划结果缺少分配卫星：{planned}')
    search.press('Enter')
    hold(page, 1200)
    row = page.locator('.el-table__body-wrapper tbody tr').first
    row.wait_for(state='visible', timeout=15000)
    row.get_by_role('button', name='详情', exact=True).click()
    dialog = page.locator('.el-dialog:visible').filter(has_text='任务详情').last
    dialog.wait_for(state='visible', timeout=15000)
    dialog.get_by_text(assigned_satellite, exact=True).wait_for(state='visible', timeout=10000)
    hold(page, 1800)
    capture(page, '27b_task_satellite_assigned', sections)
    close_dialog(page, dialog)

    open_network(page)
    progress_item = page.locator('.task-list .task-item').filter(has_text=task_name)
    progress_item.wait_for(state='visible', timeout=60000)
    progress_item.scroll_into_view_if_needed()

    started = time.monotonic()
    accelerated = False
    saw_planning = True
    saw_waiting = True
    saw_running = False
    progress_samples = []
    captured_midpoint = False
    archived = None
    timeline = [{'status': created_status, 'assignedSatellite': None, 'elapsedSeconds': 0.0}]
    last_status = created_status
    while time.monotonic() - started < 300:
        current = task_page(base_url, token, task_name)
        if current is None:
            archived = task_page(base_url, token, task_name, historical=True)
            if archived:
                break
        else:
            status = current.get('status')
            assigned_satellite = (
                current.get('assignedSatelliteName') or current.get('satellite_name')
                or assigned_satellite
            )
            if status != last_status:
                timeline.append({
                    'status': status,
                    'assignedSatellite': assigned_satellite,
                    'elapsedSeconds': round(time.monotonic() - started, 1),
                })
                last_status = status
            if page.locator('.planning-badge:visible').count() or status == '等待规划':
                saw_planning = True
            if status in ('等待规划', '等待执行'):
                saw_waiting = True
                if not accelerated and time.monotonic() - started > 4:
                    request_json(
                        base_url,
                        '/satellites/getCurrentMultiplierAndTime?multiplier=1000',
                        'POST', token=token,
                    )
                    accelerated = True
            if status == '正在执行':
                saw_running = True
                progress_item.wait_for(state='visible', timeout=15000)
                progress_item.scroll_into_view_if_needed()
                progress_value = int(progress_item.locator('.task-pct').inner_text().rstrip('%'))
                if progress_value > 0:
                    if not progress_samples or progress_samples[-1] != progress_value:
                        progress_samples.append(progress_value)
                    if len(progress_samples) == 1:
                        capture(page, '28_task_running', sections)
                    if progress_value >= 50 and not captured_midpoint:
                        captured_midpoint = True
                        capture(page, '29_task_progress_midpoint', sections)
        hold(page, 1000)

    if (not saw_planning or not saw_waiting or not saw_running or not archived
            or archived.get('status') != 'Success' or not progress_samples
            or max(progress_samples) < 50):
        raise AssertionError(
            '完整巡演任务执行过程不合格：'
            f'planning={saw_planning}, waiting={saw_waiting}, running={saw_running}, '
            f'progress={progress_samples}, archived={archived}'
        )
    if str(archived.get('task_uuid') or archived.get('taskUuid')) != str(task_uuid):
        raise AssertionError('任务 UUID 在归档前后发生变化')
    assigned_satellite = (
        archived.get('satellite_name') or archived.get('assignedSatelliteName')
        or assigned_satellite
    )
    ack = wait_until(
        lambda: find_ack(clients, task_uuid), 45, interval=0.5,
        description='客户端持久发件箱收到真实 ACK',
    )
    sys.stdout.flush()
    log_text = CAPTURE_LOG.read_text(encoding='utf-8') if CAPTURE_LOG.exists() else ''
    send_attempts = sum(
        1 for line in log_text.splitlines()
        if line.startswith('发送结果:') and task_uuid in line
    )
    retransmissions = log_text.count(f'等待 ACK 超时，将重发: {task_uuid}')
    return {
        'taskUuid': task_uuid,
        'satellite': assigned_satellite,
        'status': archived['status'],
        'sawPlanning': saw_planning,
        'sawWaiting': saw_waiting,
        'sawRunning': saw_running,
        'executionProgressSamples': progress_samples,
        'timeline': timeline,
        'ack': ack,
        'resultSendAttempts': send_attempts,
        'ackTimeoutRetransmissions': retransmissions,
    }


def show_history(page, task_name, sections):
    open_tasks(page)
    search = page.get_by_placeholder('任务名称 / 数字ID / 业务UUID', exact=True)
    search.fill(task_name)
    search.press('Enter')
    hold(page, 1800)
    page.locator('.el-tabs__item').filter(has_text='历史任务').click()
    row = page.locator('.el-table__body-wrapper tbody tr').first
    row.wait_for(state='visible', timeout=30000)
    hold(page, 2500)
    capture(page, '30_task_history_success', sections)
    page.evaluate('performance.clearResourceTimings()')
    row.get_by_role('button', name='详情', exact=True).click()
    dialog = page.locator('.el-dialog:visible').filter(has_text='任务执行结果').last
    dialog.wait_for(state='visible', timeout=15000)
    dialog.get_by_text('执行完成时间线', exact=True).wait_for(state='visible', timeout=10000)
    result_map = dialog.locator('.task-result-map')
    result_map.locator('canvas').wait_for(state='visible', timeout=30000)
    wait_for_satellite_imagery(result_map)
    hold(page, 8000)
    capture(page, '31_task_result_uuid_and_satellite', sections)
    payload_label = dialog.get_by_text('查看客户端原始回传数据', exact=True)
    payload_label.click()
    payload_label.scroll_into_view_if_needed()
    hold(page, 3500)
    payload = dialog.locator('.result-payload').inner_text()
    result = json.loads(payload)
    if result.get('result') != '成功' or result.get('execution_duration_ms', 0) <= 0:
        raise AssertionError(f'历史客户端回传不完整：{result}')
    capture(page, '32_task_client_result_payload', sections)
    dialog.get_by_role('button', name='关闭', exact=True).click()
    dialog.wait_for(state='hidden', timeout=15000)
    return result


def show_performance(page, sections):
    open_menu(page, '性能分析', '/satellite/xingneng', ready_selector='.performance-analysis')
    page.locator('.el-tabs__item').filter(has_text='系统性能分析').click()
    hold(page, 3500)
    capture(page, '33_system_performance_metrics', sections)
    detail_card = page.locator('.detail-card')
    detail_card.scroll_into_view_if_needed()
    row = detail_card.locator('tbody tr').first
    row.wait_for(state='visible', timeout=30000)
    hold(page, 2000)
    capture(page, '34_performance_evaluation_table', sections)
    row.get_by_role('button', name='详情', exact=True).click()
    drawer = page.locator('.el-drawer:visible').filter(has_text='算法评估详情').last
    drawer.wait_for(state='visible', timeout=15000)
    hold(page, 3500)
    capture(page, '35_performance_evaluation_detail', sections)
    drawer.locator('.el-drawer__close-btn').click()
    drawer.wait_for(state='hidden', timeout=15000)
    page.locator('.el-tabs__item').filter(has_text='算法性能分析').click()
    hold(page, 2000)
    cluster_select = page.locator('.cluster-card .el-select')
    cluster_select.click()
    option = page.locator('.el-select-dropdown__item:visible').first
    option.wait_for(state='visible', timeout=15000)
    option.click()
    hold(page, 4000)
    capture(page, '36_algorithm_performance_charts', sections)


def record_complete_desktop(browser, base_url, password, clients):
    viewport = {'width': 1280, 'height': 800}
    context = browser.new_context(
        viewport=viewport, record_video_dir=str(VIDEO_DIR),
        record_video_size=viewport, device_scale_factor=1, locale='zh-CN',
    )
    context.add_init_script("try { localStorage.setItem('sat_record_smooth', '1'); } catch (e) {}")
    page = context.new_page()
    page.set_default_timeout(30000)
    video = page.video
    errors = []
    failed_requests = []
    http_errors = []
    sections = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
    page.on('requestfailed', lambda request: failed_requests.append({
        'url': request.url, 'failure': request.failure,
    }))
    page.on('response', lambda response: http_errors.append({
        'url': response.url, 'status': response.status,
    }) if response.status >= 400 else None)
    task_name = f'全系统真实闭环_{RUN_ID[-6:]}'
    try:
        show_portal_and_register(page, base_url, sections)
        login(page, base_url, password)
        token = page.evaluate("localStorage.getItem('token')")
        satellite_name = show_network(page, sections)
        show_system_settings(page, sections)
        show_satellite_management(page, satellite_name, sections)
        show_task_settings(page, sections)
        show_clusters(page, sections)
        show_ground_stations(page, sections)
        show_cases(page, sections)
        show_alerts_and_replay(page, satellite_name, sections)
        open_tasks(page)
        create_task(page, task_name, settle_ms=0)
        closed_loop = run_task_closed_loop(page, base_url, token, task_name, clients, sections)
        client_result = show_history(page, task_name, sections)
        show_performance(page, sections)

        required_sections = {
            '01_portal', '03_register', '04_satellite_network',
            '05_satellite_focus_and_subtrack', '06_network_layers_and_links',
            '07_system_settings', '09_payload_parameters_optical',
            '12_satellite_management_search', '13_satellite_detail_realtime',
            '16_task_import_and_cases', '17_cluster_management', '18_cluster_detail',
            '19_ground_station_links', '20_demo_cases', '21_case_point_detail',
            '24_alert_center', '25_state_replay', '26_task_created',
            '27_task_planning', '27b_task_satellite_assigned',
            '28_task_running', '29_task_progress_midpoint',
            '30_task_history_success', '31_task_result_uuid_and_satellite',
            '32_task_client_result_payload', '33_system_performance_metrics',
            '34_performance_evaluation_table', '36_algorithm_performance_charts',
        }
        actual_sections = {item['name'] for item in sections}
        missing = sorted(required_sections - actual_sections)
        if missing:
            raise AssertionError(f'完整视频缺少功能段：{missing}')
        if errors or http_errors:
            raise AssertionError(f'浏览器验收存在错误：console={errors}, http={http_errors}')
        summary = {
            'kind': KIND, 'taskName': task_name, **closed_loop,
            'clientResult': client_result,
            'visitedSections': sections,
            'sectionCount': len(sections),
            'pageErrors': errors,
            'failedRequests': failed_requests,
            'httpErrors': http_errors,
        }
        summary_path = EVIDENCE_DIR / f'{KIND}_summary.json'
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    except Exception:
        page.screenshot(path=str(EVIDENCE_DIR / f'{KIND}_failure.png'), full_page=True)
        (EVIDENCE_DIR / f'{KIND}_failure.json').write_text(json.dumps({
            'sections': sections, 'pageErrors': errors,
            'failedRequests': failed_requests, 'httpErrors': http_errors,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({
            'kind': KIND, 'sections': sections, 'pageErrors': errors,
            'failedRequests': failed_requests, 'httpErrors': http_errors,
        }, ensure_ascii=False), flush=True)
        raise
    finally:
        context.close()

    webm_path = VIDEO_DIR / f'{KIND}_{RUN_ID}.webm'
    video.save_as(str(webm_path))
    mp4_path = OUTPUT_DIR / f'卫星项目_全系统真实运行流畅版_37功能段_{RUN_ID}.mp4'
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-n',
        '-i', str(webm_path), '-an', '-c:v', 'libx264', '-preset', 'medium',
        '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(mp4_path),
    ], check=True)
    print(f'完整桌面视频已保存：{mp4_path}', flush=True)
    return mp4_path


def main():
    os.environ.setdefault('DISPLAY', ':99')
    os.environ.setdefault('MESA_GLTHREAD', 'true')
    os.environ.setdefault('LP_NUM_THREADS', '5')
    os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
    database_path = BACKEND_DIR / f'acceptance_complete_desktop_{RUN_ID}.sqlite3'
    server_log_path = BACKEND_DIR / f'acceptance_complete_desktop_{RUN_ID}.log'
    api_port = 5700 + (os.getpid() % 200)
    base_url = f'http://127.0.0.1:{api_port}'
    socket_token = secrets.token_urlsafe(32)
    admin_password = secrets.token_urlsafe(16)
    environment = os.environ.copy()
    environment.update({
        'DATABASE_URL': f'sqlite:///{database_path}',
        'SOCKET_AUTH_TOKEN': socket_token,
        'ADMIN_INIT_PASSWORD': admin_password,
        'PORT': str(api_port),
        'PYTHONPATH': str(PROJECT_DIR / '.runtime-deps') + os.pathsep + str(BACKEND_DIR),
        'PYTHONUNBUFFERED': '1',
    })
    os.environ['SOCKET_AUTH_TOKEN'] = socket_token
    clients = []
    server_log = server_log_path.open('w', encoding='utf-8')
    original_stdout = sys.stdout
    tee = Tee(original_stdout, CAPTURE_LOG)
    sys.stdout = tee
    server = None
    try:
        server = subprocess.Popen(
            [sys.executable, 'app.py'], cwd=BACKEND_DIR, env=environment,
            stdout=server_log, stderr=subprocess.STDOUT,
        )
        health = wait_until(lambda: request_json(base_url, '/health'), 120, description='完整巡演后端就绪')
        if not health.get('database') or not health.get('occ'):
            raise AssertionError(f'完整巡演 OCC 未就绪：{health}')
        for index in range(2):
            store_path = BACKEND_DIR / f'acceptance_complete_desktop_client_{RUN_ID}_{index}.sqlite3'
            client = SatelliteClient(
                server_ip='127.0.0.1', server_port=9999, store_path=str(store_path),
                reconnect_interval=1.0, ack_timeout=1.0,
            )
            clients.append(client)
            threading.Thread(target=client.start, daemon=True).start()
        wait_until(lambda: (
            lambda current: current if current.get('networkReady') and current.get('clients') == 2 else None
        )(request_json(base_url, '/health')), 180, description='完整巡演双客户端与卫星网络就绪')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path='/usr/bin/chromium', headless=False,
                args=[
                    '--no-sandbox', '--disable-dev-shm-usage',
                    '--use-gl=angle', '--use-angle=gl', '--disable-gpu-sandbox',
                    '--ignore-gpu-blocklist', '--enable-gpu-rasterization',
                    '--window-position=0,0', '--window-size=1280,800',
                ],
            )
            try:
                record_complete_desktop(browser, base_url, admin_password, clients)
            finally:
                browser.close()
        print(f'完整巡演验收数据库与日志保留：{database_path}、{server_log_path}', flush=True)
        print(f'客户端输出与 ACK／重发证据：{CAPTURE_LOG}', flush=True)
    finally:
        for client in clients:
            try:
                client.stop()
            except Exception:
                pass
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        server_log.close()
        sys.stdout = original_stdout
        tee.close()


if __name__ == '__main__':
    main()
