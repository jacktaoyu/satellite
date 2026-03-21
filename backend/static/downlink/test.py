import os
import pickle


def load_data(filename):
    """从文件读取轨迹数据"""
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    return None  # 或返回默认值


lo = load_data("Sat_10_9_downlink.pkl")
print(lo)
