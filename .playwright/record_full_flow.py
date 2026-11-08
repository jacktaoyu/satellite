# -*- coding: utf-8 -*-
"""在独立运行库上录制真实 OCC—客户端桌面与手机闭环，不添加任何视频贴片。"""
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat
from playwright.sync_api import sync_playwright

BACKEND_DIR = Path(__file__).resolve().parents[1] / 'backend'
PROJECT_DIR = BACKEND_DIR.parent
WORK_DIR = PROJECT_DIR / '.playwright'
OUTPUT_DIR = Path('/mnt/agents/output')
RUN_ID = datetime.now().strftime('%Y%m%d_%H%M%S') + f'_{os.getpid()}'
sys.path.insert(0, str(BACKEND_DIR))
from client import SatelliteClient


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


def wait_for_satellite_imagery(locator, timeout=90000):
    """用实际地图像素连续确认影像已加载，且不是放大的低清瓦片。"""
    detail_scores = []
    edge_scores = []

    def imagery_loaded():
        image = Image.open(BytesIO(locator.screenshot(type='png'))).convert('L')
        detail_scores.append(ImageStat.Stat(image).stddev[0])
        edge_scores.append(ImageStat.Stat(image.filter(ImageFilter.FIND_EDGES)).mean[0])
        return (
            len(detail_scores) >= 2
            and min(detail_scores[-2:]) >= 24
            and min(edge_scores[-2:]) >= 7
        )

    wait_until(imagery_loaded, timeout, interval=1.0, description='清晰真实卫星影像加载并稳定')
    print(
        f'卫星影像已稳定：画面细节 {detail_scores[-1]:.1f}，边缘细节 {edge_scores[-1]:.1f}',
        flush=True,
    )
    return detail_scores[-1]


def task_page(base_url, token, task_name, historical=False):
    path = '/tasks/getOldTasks' if historical else '/tasks/getNewTasks'
    response = request_json(base_url, path, 'POST', {
        'search': task_name, 'page': 1, 'page_size': 10,
    }, token)
    items = response['data']['items']
    return items[0] if items else None


def select_option(page, placeholder, label):
    page.locator('.login-form .el-select').click()
    option = page.locator('.el-select-dropdown__item:visible').filter(has_text=label).last
    option.wait_for(state='visible', timeout=15000)
    option.click()


def login(page, base_url, password):
    page.goto(base_url + '/login', wait_until='domcontentloaded', timeout=60000)
    account = page.get_by_placeholder('请输入账号...', exact=True)
    account.wait_for(state='visible', timeout=60000)
    page.wait_for_timeout(2000)
    account.press_sequentially('admin', delay=70)
    page.get_by_placeholder('请输入密码...', exact=True).press_sequentially(password, delay=45)
    select_option(page, '请选择用户类型', '管理员')
    page.locator('.submit-btn').click()
    page.wait_for_url('**/satellite/satellite_network', timeout=60000)
    page.wait_for_timeout(5000)


def open_task_page(page, mobile):
    if mobile:
        page.get_by_role('button', name='打开导航', exact=True).click()
        page.wait_for_timeout(500)
    page.locator('.el-sub-menu__title:visible').filter(has_text='任务管理').click()
    item = page.locator('.el-menu-item:visible').filter(has_text='任务属性')
    item.wait_for(state='visible', timeout=10000)
    item.click()
    page.wait_for_url('**/satellite/renwu/shuxing', timeout=30000)
    page.get_by_role('button', name='新增任务', exact=True).wait_for(state='visible')
    page.wait_for_timeout(2500)


def open_satellite_page(page, mobile):
    if mobile:
        page.get_by_role('button', name='打开导航', exact=True).click()
        page.wait_for_timeout(500)
    item = page.locator('.el-menu-item:visible').filter(has_text='卫星网络').first
    item.wait_for(state='visible', timeout=10000)
    item.click()
    page.wait_for_url('**/satellite/satellite_network', timeout=30000)
    page.locator('.task-list').wait_for(state='visible', timeout=60000)
    page.wait_for_timeout(2500)


def create_task(page, task_name, settle_ms=2500):
    page.get_by_role('button', name='新增任务', exact=True).click()
    dialog = page.locator('.el-dialog:visible').filter(has_text='新增任务').last
    dialog.wait_for(state='visible', timeout=15000)
    dialog.get_by_placeholder('请输入任务名称', exact=True).press_sequentially(task_name, delay=65)
    dialog.locator('.el-form-item').filter(has_text='载荷类型').locator('.el-select').click()
    option = page.locator('.el-select-dropdown__item:visible').filter(has_text='光学').last
    option.wait_for(state='visible', timeout=10000)
    option.click()
    dialog.get_by_placeholder('格式: [纬度, 经度]', exact=True).press_sequentially('30, 120', delay=70)
    page.wait_for_timeout(1200)
    dialog.get_by_role('button', name='提交', exact=True).click()
    dialog.wait_for(state='hidden', timeout=30000)
    search = page.get_by_placeholder('任务名称 / 数字ID / 业务UUID', exact=True)
    search.fill(task_name)
    search.press('Enter')
    if settle_ms:
        page.wait_for_timeout(settle_ms)


def show_history_result(page, task_name, kind):
    page.locator('.el-tabs__item').filter(has_text='历史任务').click()
    page.wait_for_timeout(2500)
    page.locator('.el-table__body-wrapper tbody tr').first.wait_for(state='visible', timeout=30000)
    page.screenshot(path=str(WORK_DIR / 'evidence' / f'{kind}_history.png'), full_page=True)
    page.evaluate('performance.clearResourceTimings()')
    page.get_by_role('button', name='详情', exact=True).first.click()
    dialog = page.locator('.el-dialog:visible').filter(has_text='任务执行结果').last
    dialog.wait_for(state='visible', timeout=15000)
    dialog.get_by_text('执行完成时间线', exact=True).wait_for(state='visible', timeout=10000)
    result_map = dialog.locator('.task-result-map')
    result_map.scroll_into_view_if_needed()
    result_map.locator('canvas').wait_for(state='visible', timeout=30000)
    wait_for_satellite_imagery(result_map)
    page.wait_for_timeout(5000)
    page.screenshot(path=str(WORK_DIR / 'evidence' / f'{kind}_result_map.png'), full_page=True)
    payload_label = dialog.get_by_text('查看客户端原始回传数据', exact=True)
    payload_label.click()
    payload_label.scroll_into_view_if_needed()
    page.wait_for_timeout(1500)
    payload = dialog.locator('.result-payload').inner_text()
    result = json.loads(payload)
    if result.get('result') != '成功' or result.get('execution_duration_ms', 0) <= 0:
        raise AssertionError(f'历史客户端回传不完整：{result}')
    page.screenshot(path=str(WORK_DIR / 'evidence' / f'{kind}_result.png'), full_page=True)
    page.wait_for_timeout(3000)
    return result


def record_session(browser, base_url, password, kind, mobile):
    kind = f'{kind}_visible'
    viewport = {'width': 390, 'height': 844} if mobile else {'width': 1440, 'height': 900}
    video_dir = WORK_DIR / 'videos' / kind
    video_dir.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(
        viewport=viewport,
        record_video_dir=str(video_dir),
        record_video_size=viewport,
        is_mobile=mobile,
        has_touch=mobile,
        device_scale_factor=1,
        locale='zh-CN',
    )
    page = context.new_page()
    page.set_default_timeout(30000)
    errors = []
    failed_requests = []
    http_errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
    page.on('requestfailed', lambda request: failed_requests.append({
        'url': request.url, 'failure': request.failure,
    }))
    page.on('response', lambda response: http_errors.append({
        'url': response.url, 'status': response.status,
    }) if response.status >= 400 else None)
    task_name = f'{"手机" if mobile else "桌面"}闭环_{RUN_ID[-6:]}'
    video = page.video
    archived = None
    result = None
    try:
        login(page, base_url, password)
        token = page.evaluate("localStorage.getItem('token')")
        open_task_page(page, mobile)
        create_task(page, task_name)
        created = wait_until(
            lambda: task_page(base_url, token, task_name), 30,
            description=f'{kind}任务创建入库',
        )
        task_uuid = created['task_uuid'] or created.get('taskUuid')
        started = time.monotonic()
        accelerated = False
        saw_waiting = False
        saw_running = False
        progress_text = None
        open_satellite_page(page, mobile)
        progress_item = page.locator('.task-list .task-item').filter(has_text=task_name)
        progress_item.wait_for(state='visible', timeout=60000)
        progress_item.scroll_into_view_if_needed()
        page.screenshot(path=str(WORK_DIR / 'evidence' / f'{kind}_planning.png'), full_page=True)
        progress_samples = []
        captured_midpoint = False
        while time.monotonic() - started < 300:
            current = task_page(base_url, token, task_name)
            if current is None:
                archived = task_page(base_url, token, task_name, historical=True)
                if archived:
                    break
            else:
                status = current['status']
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
                    progress_text = progress_item.locator('.task-pct').inner_text()
                    progress_value = int(progress_text.rstrip('%'))
                    if progress_value > 0:
                        if not progress_samples or progress_samples[-1] != progress_value:
                            progress_samples.append(progress_value)
                        if len(progress_samples) == 1:
                            page.screenshot(
                                path=str(WORK_DIR / 'evidence' / f'{kind}_network_running.png'),
                                full_page=True,
                            )
                        if progress_value >= 50 and not captured_midpoint:
                            captured_midpoint = True
                            page.screenshot(
                                path=str(WORK_DIR / 'evidence' / f'{kind}_network_midpoint.png'),
                                full_page=True,
                            )
            page.wait_for_timeout(1000)
        if (not saw_waiting or not saw_running or not archived
                or archived['status'] != 'Success' or not progress_samples
                or max(progress_samples) < 50):
            raise AssertionError(
                f'{kind}执行过程展示不完整：waiting={saw_waiting}, running={saw_running}, '
                f'progress={progress_samples}, archived={archived}'
            )
        open_task_page(page, mobile)
        search = page.get_by_placeholder('任务名称 / 数字ID / 业务UUID', exact=True)
        search.fill(task_name)
        search.press('Enter')
        page.wait_for_timeout(1500)
        page.screenshot(path=str(WORK_DIR / 'evidence' / f'{kind}_completed.png'), full_page=True)
        result = show_history_result(page, task_name, kind)
        if str(archived.get('task_uuid') or archived.get('taskUuid')) != str(task_uuid):
            raise AssertionError(f'{kind}任务 UUID 在归档前后发生变化')
        summary = {
            'kind': kind,
            'taskName': task_name,
            'taskUuid': task_uuid,
            'satellite': archived.get('satellite_name') or archived.get('assignedSatelliteName'),
            'status': archived['status'],
            'sawWaiting': saw_waiting,
            'sawRunning': saw_running,
            'executionProgress': progress_text,
            'executionProgressSamples': progress_samples,
            'clientResult': result,
            'pageErrors': errors,
            'failedRequests': failed_requests,
            'httpErrors': http_errors,
        }
        (WORK_DIR / 'evidence' / f'{kind}_summary.json').write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    except Exception:
        page.screenshot(path=str(WORK_DIR / 'evidence' / f'{kind}_failure.png'), full_page=True)
        (WORK_DIR / 'evidence' / f'{kind}_failure.json').write_text(json.dumps({
            'pageErrors': errors, 'failedRequests': failed_requests, 'httpErrors': http_errors,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'kind': kind, 'pageErrors': errors}, ensure_ascii=False), flush=True)
        raise
    finally:
        context.close()
    webm_path = WORK_DIR / 'videos' / f'{kind}_{RUN_ID}.webm'
    video.save_as(str(webm_path))
    mp4_path = OUTPUT_DIR / (f'手机完整功能演示_{RUN_ID}.mp4' if mobile else f'桌面完整功能演示_{RUN_ID}.mp4')
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-n',
        '-i', str(webm_path), '-an', '-c:v', 'libx264', '-preset', 'medium',
        '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(mp4_path),
    ], check=True)
    print(f'{kind}视频已保存：{mp4_path}', flush=True)


def main():
    database_path = BACKEND_DIR / f'acceptance_browser_{RUN_ID}.sqlite3'
    server_log_path = BACKEND_DIR / f'acceptance_browser_{RUN_ID}.log'
    api_port = 5400 + (os.getpid() % 200)
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
    server = subprocess.Popen(
        [sys.executable, 'app.py'], cwd=BACKEND_DIR, env=environment,
        stdout=server_log, stderr=subprocess.STDOUT,
    )
    try:
        health = wait_until(lambda: request_json(base_url, '/health'), 120, description='录屏后端就绪')
        if not health.get('database') or not health.get('occ'):
            raise AssertionError(f'录屏 OCC 未就绪：{health}')
        for index in range(2):
            store_path = BACKEND_DIR / f'acceptance_browser_client_{RUN_ID}_{index}.sqlite3'
            client = SatelliteClient(
                server_ip='127.0.0.1', server_port=9999, store_path=str(store_path),
                reconnect_interval=1.0, ack_timeout=5.0,
            )
            clients.append(client)
            threading.Thread(target=client.start, daemon=True).start()
        wait_until(lambda: (
            lambda current: current if current.get('networkReady') and current.get('clients') == 2 else None
        )(request_json(base_url, '/health')), 180, description='录屏双客户端与卫星网络就绪')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path='/usr/bin/chromium', headless=True,
                args=[
                    '--no-sandbox', '--disable-dev-shm-usage', '--enable-unsafe-swiftshader',
                    '--use-gl=angle', '--use-angle=swiftshader', '--disable-gpu-sandbox',
                ],
            )
            try:
                kinds = sys.argv[1:] or ['desktop', 'mobile']
                if any(kind not in ('desktop', 'mobile') for kind in kinds):
                    raise ValueError('录屏类型仅支持 desktop 或 mobile')
                for kind in kinds:
                    record_session(browser, base_url, admin_password, kind, kind == 'mobile')
            finally:
                browser.close()
        print(f'录屏验收数据库与日志保留：{database_path}、{server_log_path}', flush=True)
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


if __name__ == '__main__':
    main()
