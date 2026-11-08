import socket
import threading
import json
import os
import time
from queue import Queue

from client_store import ClientResultStore


class SatelliteClient:
    def __init__(self, server_ip='localhost', server_port=9999, store_path=None,
                 reconnect_interval=2.0, ack_timeout=5.0):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_socket = None
        self.result_queue = Queue()
        self.is_running = True
        self.reconnect_interval = reconnect_interval
        self.ack_timeout = ack_timeout
        self.store = ClientResultStore(
            store_path or os.environ.get('CLIENT_STORE_PATH', 'satellite_client.sqlite3')
        )
        self.socket_lock = threading.RLock()
        self.workers_lock = threading.Lock()
        self.workers = set()
        self.connected = threading.Event()
        self.stop_event = threading.Event()
        self.ack_events = {}
        self.ack_events_lock = threading.Lock()

    def connect(self):
        """连接到服务端；连接密钥只从运行环境读取。"""
        token = os.environ.get('SOCKET_AUTH_TOKEN')
        if not token:
            print('连接服务端失败：请设置环境变量 SOCKET_AUTH_TOKEN')
            return False
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(10)
            client_socket.connect((self.server_ip, self.server_port))
            client_socket.sendall((json.dumps({"token": token}) + "\n").encode())
            client_socket.settimeout(1.0)
            with self.socket_lock:
                self.client_socket = client_socket
            self.connected.set()
            print(f"已连接到服务端 {self.server_ip}:{self.server_port}")
            return True
        except Exception as e:
            print(f"连接服务端失败: {str(e)}")
            self._close_socket()
            return False

    def start(self):
        """启动客户端；接收线程自动重连，发送线程持续处理持久发件箱。"""
        self.is_running = True
        self.stop_event.clear()
        recv_thread = threading.Thread(target=self._receive_tasks, daemon=True)
        send_thread = threading.Thread(target=self._send_results, daemon=True)
        recv_thread.start()
        send_thread.start()
        try:
            while self.is_running:
                self.stop_event.wait(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """幂等停止；未执行完的任务不会生成伪成功结果。"""
        if not self.is_running and self.stop_event.is_set():
            return
        self.is_running = False
        self.stop_event.set()
        self._close_socket()
        with self.workers_lock:
            workers = list(self.workers)
        for worker in workers:
            if worker is not threading.current_thread():
                worker.join(timeout=2)
        self.store.close()
        print("客户端已停止")

    def _close_socket(self):
        self.connected.clear()
        with self.socket_lock:
            client_socket = self.client_socket
            self.client_socket = None
        if client_socket:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                client_socket.close()
            except OSError:
                pass

    def _handle_ack(self, msg):
        task_uuid = msg.get('task_uuid')
        if not task_uuid:
            return
        if msg.get('type') == 'ack':
            self.store.mark_ack(task_uuid)
            print(f"结果已确认: {task_uuid}")
        else:
            self.store.mark_nack(task_uuid, msg.get('message', '服务端拒绝结果'))
            print(f"结果被拒绝: {task_uuid}, {msg.get('message', '')}")
        with self.ack_events_lock:
            event = self.ack_events.get(task_uuid)
        if event:
            event.set()

    def _receive_tasks(self):
        """接收任务与 ACK/NACK；连接断开后保留发件箱并自动重连。"""
        buffer = b""
        while self.is_running:
            if not self.connected.is_set():
                if not self.connect():
                    self.stop_event.wait(self.reconnect_interval)
                    continue
                buffer = b""
            try:
                with self.socket_lock:
                    client_socket = self.client_socket
                if client_socket is None:
                    continue
                data = client_socket.recv(4096)
                if not data:
                    raise ConnectionError('服务端关闭连接')
                buffer += data
                while b'\n' in buffer:
                    msg_str, buffer = buffer.split(b'\n', 1)
                    if not msg_str.strip():
                        continue
                    try:
                        msg = json.loads(msg_str.decode())
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}")
                        continue
                    if msg.get('type') in ('ack', 'nack'):
                        self._handle_ack(msg)
                        continue
                    print(f"收到任务: {msg}")
                    task_thread = threading.Thread(target=self._execute_task, args=(msg,), daemon=True)
                    with self.workers_lock:
                        self.workers.add(task_thread)
                    task_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"接收任务出错: {str(e)}，准备重连")
                self._close_socket()
                self.stop_event.wait(self.reconnect_interval)
        print("客户端接收线程已停止")

    def _execute_task(self, task_msg):
        """按真实墙钟等待执行，仿真倍速不影响执行耗时。"""
        try:
            task_uuid = task_msg.get('task_uuid') or f"legacy-{task_msg['task_id']}"
            if self.store.has_result(task_uuid):
                print(f"跳过已处理任务: {task_uuid}")
                return
            execute_time = max(0.0, float(task_msg['execute_time']))
            print(f"执行任务: {task_msg['task_id']} ({task_uuid})")
            started_at = time.monotonic()
            if self.stop_event.wait(execute_time):
                print(f"任务已停止，不回传成功结果: {task_uuid}")
                return
            duration_ms = max(0, round((time.monotonic() - started_at) * 1000))
            if not self.is_running:
                return
            result = {
                "task_id": task_msg['task_id'],
                "task_uuid": task_uuid,
                "execution_duration_ms": duration_ms,
                "result": "成功"
            }
            if self.store.enqueue_result(result):
                self.result_queue.put(result)
        except Exception as e:
            print(f"执行任务出错: {str(e)}")
        finally:
            with self.workers_lock:
                self.workers.discard(threading.current_thread())

    def _send_results(self):
        """逐条发送并等待 ACK；超时或断线不删除发件箱记录。"""
        while self.is_running:
            if not self.connected.wait(timeout=0.5):
                continue
            pending = self.store.pending_results()
            if not pending:
                self.stop_event.wait(0.1)
                continue
            for result in pending:
                if not self.is_running or not self.connected.is_set():
                    break
                task_uuid = result['task_uuid']
                event = threading.Event()
                with self.ack_events_lock:
                    self.ack_events[task_uuid] = event
                try:
                    data = json.dumps(result, ensure_ascii=False) + "\n"
                    with self.socket_lock:
                        if self.client_socket is None:
                            raise ConnectionError('连接不可用')
                        self.client_socket.sendall(data.encode())
                    print(f"发送结果: {result}")
                    if not event.wait(self.ack_timeout) and self.is_running:
                        print(f"等待 ACK 超时，将重发: {task_uuid}")
                except Exception as e:
                    if self.is_running:
                        print(f"发送结果出错: {str(e)}")
                    self._close_socket()
                finally:
                    with self.ack_events_lock:
                        self.ack_events.pop(task_uuid, None)
                self.stop_event.wait(0.1)


def get_server_ip():
    """获取用户输入的服务器IP地址"""
    while True:
        ip = input("请输入服务器IP地址: ").strip()
        if all(part.isdigit() and 0 <= int(part) <= 255
               for part in ip.split('.')) and len(ip.split('.')) == 4:
            return ip
        print("IP地址格式不正确，请重新输入！")


if __name__ == "__main__":
    print("卫星任务执行客户端")
    print("=" * 30)
    server_ip = get_server_ip()
    client = SatelliteClient(server_ip=server_ip)
    client.start()
