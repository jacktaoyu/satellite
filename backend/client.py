import socket
import threading
import json
import os
import time
from queue import Queue


class SatelliteClient:
    def __init__(self, server_ip='localhost', server_port=9999):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = None
        self.result_queue = Queue()
        self.is_running = True

    def connect(self):
        """连接到服务端"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, self.server_port))
            # 连接后首先发送鉴权握手消息（与服务端 SOCKET_AUTH_TOKEN 对应）
            token = os.environ.get('SOCKET_AUTH_TOKEN', 'dev-satellite-token')
            self.client_socket.sendall((json.dumps({"token": token}) + "\n").encode())
            print(f"已连接到服务端 {self.server_ip}:{self.server_port}")
            return True
        except Exception as e:
            print(f"连接服务端失败: {str(e)}")
            return False

    def start(self):
        """启动客户端"""
        if not self.connect():
            return

        # 创建接收线程
        recv_thread = threading.Thread(target=self._receive_tasks)
        # 创建发送线程
        send_thread = threading.Thread(target=self._send_results)

        recv_thread.daemon = True
        send_thread.daemon = True

        recv_thread.start()
        send_thread.start()

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止客户端"""
        self.is_running = False
        if self.client_socket:
            self.client_socket.close()
        print("客户端已停止")

    def _receive_tasks(self):
        """接收任务线程"""
        buffer = b""
        while self.is_running:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break

                buffer += data
                # 按换行符分割消息
                while b'\n' in buffer:
                    msg_str, buffer = buffer.split(b'\n', 1)
                    try:
                        # 解析JSON消息
                        msg = json.loads(msg_str.decode())
                        print(f"收到任务: {msg}")
                        # 创建新线程执行任务
                        task_thread = threading.Thread(
                            target=self._execute_task,
                            args=(msg,)
                        )
                        task_thread.daemon = True
                        task_thread.start()
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}")
                        continue
            except Exception as e:
                print(f"接收任务出错: {str(e)}")
                break
        # 接收线程退出（与服务端断连），置标志让主循环退出，避免空转
        self.is_running = False
        print("与服务端的连接已断开，客户端退出")

    def _execute_task(self, task_msg):
        """执行任务"""
        try:
            # 模拟任务执行时间
            print(f"执行任务: {task_msg['task_id']}")
            time.sleep(task_msg['execute_time'])
            # 将结果放入队列
            result = {
                "task_id": task_msg['task_id'],
                "result": "成功"
            }
            self.result_queue.put(result)
        except Exception as e:
            print(f"执行任务出错: {str(e)}")

    def _send_results(self):
        """发送结果线程"""
        while self.is_running:
            try:
                # 检查结果队列
                if not self.result_queue.empty():
                    result = self.result_queue.get()
                    # 发送结果到服务端
                    print(f"发送结果: {result}")
                    # 确保发送完整JSON数据，添加换行符作为消息分隔符
                    data = json.dumps(result) + "\n"
                    self.client_socket.sendall(data.encode())
                else:
                    time.sleep(0.1)  # 避免忙等占满CPU
            except Exception as e:
                print(f"发送结果出错: {str(e)}")
                break


def get_server_ip():
    """获取用户输入的服务器IP地址"""
    while True:
        ip = input("请输入服务器IP地址: ").strip()
        # 简单的IP地址格式验证
        if all(part.isdigit() and 0 <= int(part) <= 255
               for part in ip.split('.')) and len(ip.split('.')) == 4:
            return ip
        print("IP地址格式不正确，请重新输入！")


if __name__ == "__main__":
    print("卫星任务执行客户端")
    print("=" * 30)

    # 获取服务器IP地址
    server_ip = get_server_ip()

    # 创建并启动客户端
    client = SatelliteClient(server_ip=server_ip)
    client.start()
