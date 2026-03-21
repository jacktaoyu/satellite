import time
from queue import Queue


class DataCenter:
    """
    数据中心,负责实时地从卫星接收原始数据，并进行处理，返回给控制中心
    """

    def __init__(self):
        self.raw_data_queue = Queue()  # 接收原始数据

    def receive_raw_data(self):
        """
        从卫星中接收原始数据
        """
        if not self.raw_data_queue.empty():
            raw_data_list = self.raw_data_queue.get()
            print(f"数据中心接收原始数据: {raw_data_list}")
            return raw_data_list
        return None

    # 处理数据（简单实现）
    def processing_data(self, raw_data_list):
        """
        处理数据（简单实现）
        """
        if not raw_data_list:
            return None
        # # 简单的数据处理：添加处理标记
        # for result in raw_data_list:
        #     result["data"] =
        return raw_data_list

    def return_data(self, processed_data):
        """
        将处理后的数据返回给控制中心
        """
        if processed_data:
            print(f"数据中心返回处理后的数据的长度: {len(processed_data)}")
            # self.processed_data_queue.put(processed_data)
            return True
        return False

    def run(self, occ_result_queue):
        """
        数据中心线程运行函数
        """
        print("数据中心线程启动")

        while True:
            # 接收原始数据
            raw_data = self.receive_raw_data()
            if raw_data:
                # 处理数据
                processed_data = self.processing_data(raw_data)

                # 返回处理后的数据
                if processed_data:
                    self.return_data(processed_data)
                    occ_result_queue.put(processed_data)

            time.sleep(5)  # 控制处理频率
