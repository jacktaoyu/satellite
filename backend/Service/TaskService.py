import random
import time
from skyfield.api import wgs84, load


# 任务类
class Task:
    """
    任务类,负责存储任务信息
    """

    def __init__(self, task_id, task_name,
                 target_location, cluster_name, latest_end_time, earliest_start_time, sensor_type=None, resolution=0.5,
                 priority=1, boundary_points=None, is_emergency=False, task_type="点目标", cycle_time=3600,
                 parent_task_id=None, appointment_time=None, cloud_thickness=0, parent_location=None, parent_type=None):
        """
        初始化任务
        :param task_id: 任务ID
        :param priority: 优先级
        :param is_emergency: 是否紧急
        :param task_type: 任务类型
        :param sensor_type: 载荷类型
        :param resolution: 分辨率
        :param earliest_start_time: 任务的最早开始时间
        :param latest_end_time: 任务的最晚结束时间
        :param target_location: 观测位置 [纬度, 经度]
        """
        # 各种自定义属性
        self.task_id = task_id  # 任务的唯一标识符
        self.task_name = task_name
        self.priority = priority  # 任务的优先级
        self.is_emergency = is_emergency  # 是否是紧急任务
        self.sensor_type = sensor_type  # 指定任务执行时要使用的载荷类型
        self.task_type = task_type  # 任务类型
        self.parent_type = parent_type if parent_type else self.task_type  # 父任务类型
        self.resolution = resolution  # 分辨率要求
        self.target_location = target_location  # 观测位置 [纬度, 经度]
        # 区域任务相关属性
        self.boundary_points = boundary_points  # 区域边界点列表 [(lat1, lon1), (lat2, lon2), ...]
        self.earliest_start_time = earliest_start_time  # 任务的最早开始时间
        self.latest_end_time = latest_end_time  # 任务的最晚结束时间
        self.cycle_time = cycle_time  # 单位（秒） 任务的周期时间，默认为3600
        self.appointment_time = appointment_time  # 任务的预约时间

        self.cloud_thickness = cloud_thickness  # 单位：m 目标点的云层厚度，影响红外和光学载荷

        self.parent_task_id = parent_task_id  # 父任务ID（用于子任务）
        self.parent_location = parent_location  # 任务的父任务位置
        self.friend_task = None  # 任务的合并任务
        self.subtasks = []  # 子任务列表
        self.subtask_ids = []  # 子任务ID列表

        self.cluster_name = cluster_name  # 所属星簇name

        # 任务的执行时属性
        self.target_attitude = None  # 目标姿态四元数
        self.side_swing_angle = 0.0  # 任务需要的成像角度，初始为0
        self.time_window = None  # 任务的时间窗口，初始为None
        self.available_time_window = None  # 任务的最终可执行时间窗口
        self.status = "等待规划"  # 状态
        self.execution_time = 0.0  # 执行要耗费的时间
        # self.is_illumination = False  # 是否有光照
        # self.cloud_thickness = 0.0  # 单位：km 目标点的云层厚度，影响红外和光学载荷
        self.assigned_satellite = None  # 该任务分配到的卫星
        self.battery_befor_task = None  # 任务执行前剩余的电池电量
        self.battery_after_task = None  # 任务执行完毕后剩余的电池电量
        self.storge_befor_task = None  # 任务执行前剩余的存储量
        # self.storge_after_task = None  # 任务执行完毕后消耗的存储量
        self.current_storage = None  # 任务执行完毕后消耗的存储量

        self.visible_windows = {}  # 存储每个卫星的可见时间窗口
        # self.available_satellites = []  # 可用卫星列表及其时间窗口
        self.comment = None  # 任务的备注

        # 时间备份,用于重规划时回复时间
        self.earliest_start_time_backup = earliest_start_time
        self.latest_end_time_backup = latest_end_time
        self.is_replan = False

        # self.is_area_task = boundary_points is not None and len(boundary_points) >= 3

    def __lt__(self, other):
        return self.priority > other.priority  # 定义比较规则,优先级大的排在前面

    def get_task_fields(self):
        """
        获取任务的字段列表
        :return: 包含所有任务字段的列表
        """
        fields = str(self.task_id) + "|" + self.sensor_type + "|" + str(self.target_location) + "|" + str(
            self.execution_time) + "|" + str(self.assigned_satellite.sat_name) + "|" + str(self.available_time_window)
        return fields

    # 检查任务位置在指定时间是否有光照
    def check_illumination(self, time_point=None):
        """
        检查任务位置在指定时间是否有光照（是否处于日照区）
        :param time_point: 指定的时间点，默认为当前时间
        :return: 布尔值，True表示有光照，False表示无光照
        """
        # 如果任务位置未设置，则无法计算
        if self.target_location is None:
            print(f"任务{self.task_id}位置未设置，无法计算光照情况")
            return None

        try:
            # 加载星历数据和时间尺度
            ts = load.timescale()

            try:
                # 尝试加载星历数据
                planets = load('./library/de421.bsp')
            except Exception as e:
                print(f"加载星历数据失败: {e}")
                return self._simple_illumination_estimation()

            earth = planets['earth']
            sun = planets['sun']

            # 使用指定时间或当前时间
            t = time_point if time_point is not None else ts.now()

            # 将任务位置转换为地球表面点
            task_target_location = wgs84.latlon(self.target_location[0], self.target_location[1])

            # 获取太阳位置和任务位置（地球坐标系）
            # sun_geocentric = earth.at(t).observe(sun)
            task_geocentric = (earth + task_target_location).at(t)

            # 计算太阳高度角
            # sunpos = sun_geocentric.apparent()
            # 从任务位置观测太阳
            task_sunpos = task_geocentric.observe(sun).apparent()
            # 获取高度角
            alt, az, distance = task_sunpos.altaz()

            # 如果太阳高度角大于0，表示有光照
            is_illuminated = alt.degrees > 0

            return is_illuminated

        except Exception as e:
            print(f"光照计算出错: {e}")
            return self._simple_illumination_estimation()

    def _simple_illumination_estimation(self):
        """
        简单的光照估算，基于当前时间
        :return: 是否有光照的简单估计
        """
        # 获取当前时间（小时）
        hour = time.localtime().tm_hour

        # 简单估计：6点到18点之间是白天
        is_daytime = 6 <= hour < 18

        print(f"使用简单估算：当前时间 {hour}时，{'白天' if is_daytime else '夜间'}")
        return is_daytime

    def get_cloud_thickness(self):
        """
        随机获取云层厚度
        """
        return random.randint(0, 1000)


if __name__ == '__main__':
    pass
