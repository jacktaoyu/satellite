# -*- coding: utf-8 -*-
"""client.py 闭环集成测试：模拟服务端 9999 端口，验证 连接→收任务→执行→回传结果 全流程"""
import socket
import threading
import json
import time
import sys

sys.path.insert(0, '.')
from client import SatelliteClient


def run_mock_server(result_holder, ready_event):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', 9999))
    srv.listen(1)
    ready_event.set()
    conn, addr = srv.accept()
    print(f"[服务端] 客户端已连接: {addr}")

    # 下发一个测试任务（换行符分隔，与 SatelliteNetwork._send_tasks 协议一致）
    task = {"task_id": 999, "execute_time": 1}
    conn.sendall((json.dumps(task) + "\n").encode())
    print(f"[服务端] 已下发任务: {task}")

    # 接收客户端回传结果
    buffer = b""
    conn.settimeout(15)
    try:
        while b'\n' not in buffer:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data
        if buffer:
            result_holder.append(json.loads(buffer.decode().strip()))
    except socket.timeout:
        print("[服务端] 等待结果超时")
    conn.close()
    srv.close()


def test_closed_loop():
    """正常路径：客户端连接 9999，收到任务执行后回传结果"""
    results = []
    ready = threading.Event()
    server_thread = threading.Thread(target=run_mock_server, args=(results, ready), daemon=True)
    server_thread.start()
    ready.wait(timeout=5)

    client = SatelliteClient(server_ip='127.0.0.1')  # 默认端口应为 9999
    assert client.server_port == 9999, f"默认端口错误: {client.server_port}"

    client.connect()
    recv_t = threading.Thread(target=client._receive_tasks, daemon=True)
    send_t = threading.Thread(target=client._send_results, daemon=True)
    recv_t.start()
    send_t.start()

    server_thread.join(timeout=20)
    client.stop()

    assert results, "服务端未收到客户端回传的任务结果"
    assert results[0]['task_id'] == 999, f"task_id 不匹配: {results[0]}"
    assert results[0]['result'] == "成功", f"result 不匹配: {results[0]}"
    print("✅ 正常路径测试通过：任务下发→执行→结果回传闭环完整")


def test_connect_refused():
    """异常路径：服务端未启动时，客户端应优雅报错而非崩溃"""
    client = SatelliteClient(server_ip='127.0.0.1', server_port=19999)
    ok = client.connect()
    assert ok is False, "连接不存在的服务端应返回 False"
    print("✅ 异常路径测试通过：连接被拒绝时返回 False 并打印错误")


if __name__ == '__main__':
    test_closed_loop()
    test_connect_refused()
    print("\n全部测试通过")
