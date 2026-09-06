# -*- coding: utf-8 -*-
"""启动 NODES 个模拟卫星客户端连接后端 9999 端口。

后端 SatelliteNetwork._start_socket_server() 会阻塞等待 NODES(=2) 个客户端连接，
未连接时卫星网络线程不运行（is_trace=False），规划不会启动。
本脚本复用 client.SatelliteClient，供压测/验收时快速拉起模拟客户端。
用法: myvenv/bin/python3 run_mock_clients.py  (前台常驻)
"""
import sys
import threading
import time

sys.path.insert(0, '.')
from client import SatelliteClient

N = 2  # 与 config.NODES 保持一致


def main():
    clients = []
    for i in range(N):
        c = SatelliteClient(server_ip='127.0.0.1')
        if not c.connect():
            print(f"客户端 {i} 连接失败")
            sys.exit(1)
        threading.Thread(target=c._receive_tasks, daemon=True).start()
        threading.Thread(target=c._send_results, daemon=True).start()
        clients.append(c)
        print(f"模拟客户端 {i} 已连接 127.0.0.1:9999")
    print(f"{N} 个模拟客户端全部就绪，保持运行中...")
    # 所有客户端断连（is_running 被接收线程置 False）后退出，避免空转
    while any(c.is_running for c in clients):
        time.sleep(1)
    print("所有模拟客户端均已断开，退出")


if __name__ == '__main__':
    main()
