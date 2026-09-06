import copy
import math
import random
import numpy as np
import datetime
from datetime import datetime, timedelta, timezone
from Service.Ant import AntColonyOptimizer
from Service.Genetic import GeneticAlgorithm
from Service.Greedy import GreedyScheduler as GreedyAlgorithm
from skyfield.api import EarthSatellite, load


class Task:
    def __init__(self, task_id, target_location, priority, sensor_type, task_type, cluster_names,
                 earliest_start_time=None, latest_end_time=None, cloud_extent=0, light_power=0,
                 target_length=10000, target_width=10000, resolution=1.0, task_name="noname_task",
                 boundary_points=None, parent_task_id=None, visible_windows=None):
        self.task_id = task_id
        self.target_location = target_location  # (纬度, 经度)
        self.priority = priority  # 1-5，5为最高优先级
        self.sensor_type = sensor_type  # 'optical' 或 'SAR'
        self.earliest_start_time = earliest_start_time
        self.latest_end_time = latest_end_time
        self.target_attitude = None  # 目标姿态四元数
        self.target_length = target_length  # 目标区域长度（米）
        self.target_width = target_width  # 目标区域宽度（米）
        self.resolution = resolution  # 目标分辨率（米）
        self.visible_windows = visible_windows or {}  # 存储每个卫星的可见时间窗口
        self.available_satellites = []  # 可用卫星列表及其时间窗口
        self.task_type = task_type
        self.storage_added = 0
        self.cluster_names = cluster_names if isinstance(cluster_names, list) else [cluster_names]
        # 区域任务相关属性
        self.boundary_points = boundary_points  # 区域边界点列表 [(lat1, lon1), (lat2, lon2), ...]
        self.parent_task_id = parent_task_id  # 父任务ID（用于子任务）
        self.is_area_task = boundary_points is not None and len(boundary_points) >= 3
        self.cloud_extent = cloud_extent
        self.light_power = light_power
        self.task_name = task_name

    def add_available_satellite(self, satellite, tw_start, tw_end):
        """添加可用卫星及其时间窗口"""
        self.available_satellites.append({
            'satellite': satellite,
            'tw_start': tw_start,
            'tw_end': tw_end
        })


class Satellite:
    def __init__(self, sat_id, tle_line1, tle_line2, sensor_type, resolution_capability, cluster_names, imaging_powers,
                 sunlight_powers, eclipse_powers, max_pitch_angle, payload_params,
                 battery_capacity, data_storage, downlink_rate=4000,
                 downlink_windows=None, charging_windows=None, swath_width=None, simulation_start_time=None, tasks=[],
                 initial_battery=5000, initial_storage=0, max_slew_rate=None, max_roll_angle=None):
        # 基本信息
        self.sat_id = sat_id
        self.tle_line1 = tle_line1
        self.tle_line2 = tle_line2
        self.sensor_type = sensor_type  # 'optical' 或 'SAR'或'infrared'
        self.resolution_capability = resolution_capability  # 分辨率能力（米）
        self.initial_battery = battery_capacity
        # 资源信息
        self.battery_capacity = battery_capacity  # 电池容量（瓦时）
        self.data_storage = data_storage  # 数据存储容量（GB）
        if cluster_names is None:
            self.cluster_names = None
        elif isinstance(cluster_names, list):
            self.cluster_names = cluster_names
        else:
            self.cluster_names = [cluster_names]
        # 初始状态
        self.battery_level = battery_capacity if initial_battery is None else initial_battery
        self.battery_level = min(battery_capacity, self.battery_level)
        self.current_storage = initial_storage
        self.current_attitude = np.array([1, 0, 0, 0])  # 单位四元数，表示卫星初始姿态
        self.downlink_rate = downlink_rate
        self.ts = load.timescale()
        self.satellite = EarthSatellite(tle_line1, tle_line2, self.sat_id, self.ts)
        # 设置默认载荷参数
        if payload_params is None:
            self.payload_params = self._get_default_payload_params(sensor_type)
        else:
            self.payload_params = payload_params

        # 明确设置初始状态的时间点
        if simulation_start_time is None:

            # 默认使用 2023-10-01 00:00:00
            self.simulation_start_time = datetime(2023, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            self.simulation_start_time = simulation_start_time
        # 任务和时间窗口
        self.downlink_windows = downlink_windows or []  # 数据下行时间窗口
        self.charging_windows = charging_windows or []  # 时间窗口（日照期）
        self.occupied_time = []  # 任务占用时间段 [(start_time1, end_time1), ...]
        if tasks is None:
            self.tasks = []  # 已分配的任务记录
        else:
            self.tasks = tasks
        self.last_update_time = None  # 上次状态更新时间
        if max_pitch_angle is None:
            self.max_pitch_angle = 45.0
        else:
            self.max_pitch_angle = max_pitch_angle
        # 轨道参数（从TLE计算）
        self.orbit_height = self._calculate_orbit_height()  # 轨道高度（千米）
        if imaging_powers is None:
            # 电源参数
            self.imaging_powers = {
                'optical': 450,  # 光学载荷取中间值
                'SAR': 1000,  # 兼顾X/C波段
                'infrared': 650  # 制冷型红外
            }
        else:
            self.imaging_powers = imaging_powers
        if sunlight_powers is None:
            self.sunlight_powers = {
                'maneuver': 500,  # 中等敏捷卫星
                'idle': 10,  # 通用基线
                'charge': 300  # 平均充电功率
            }
        else:
            self.sunlight_powers = sunlight_powers
        if eclipse_powers is None:
            self.eclipse_powers = {
                'maneuver': 500,  # 与光照区一致
                'idle': 8  # 极限省电模式
            }
        else:
            self.eclipse_powers = eclipse_powers
        self.state_timeline = {
            self.simulation_start_time: {
                'battery_level': self.battery_level,
                'current_storage': self.current_storage,
                'attitude': self.current_attitude.copy() if hasattr(self, 'current_attitude') else np.array(
                    [1, 0, 0, 0])
            }
        }
        # print(f"卫星初始化状态为{self.state_timeline}")
        self.boundary_quaternions = calculate_boundary_quaternions()
        # 成像性能参数
        # 扫描宽度（米）- 新增参数
        self.swath_width = swath_width
        if self.swath_width is None:
            # 默认值，根据卫星类型和轨道高度设置
            if sensor_type == 'optical':
                # 光学扫描宽度估算：约为轨道高度的20%
                self.swath_width = self.orbit_height * 1 * 0.2  # 转换为km
            else:  # 'SAR'
                # SAR扫描宽度估算：约为轨道高度的30%
                self.swath_width = self.orbit_height * 1 * 0.3  # 转换为km

            # 确保值在合理范围内
            self.swath_width = min(max(self.swath_width, 10), 100)  # 10-100公里范围

        # 卫星姿态机动性能参数
        # 最大转动速率(度/秒)
        self.max_slew_rate = max_slew_rate or 3.0

        # 最大侧摆角(度)
        self.max_roll_angle = max_roll_angle
        if self.max_roll_angle is None:
            # 光学卫星一般侧摆能力更强
            self.max_roll_angle = 45.0 if sensor_type == 'optical' else 30.0

        self.cloud_thresholds = {
            'optical': 0.2,  # 可见光，要求较低的云雾 (例如 20% 阈值)
            'SAR': 1.1,  # SAR不受云雾影响，设置一个大于1的值，表示没有实际限制
            'infrared': 0.6  # 红外，比可见光要求低 (例如 60% 阈值)
            # 如果需要，可以根据 self.sensor_type 覆盖或添加更具体的阈值
            # 例如，如果主传感器是光学，可以默认将 satellite.cloud_threshold 设置为 0.2
            # 但为了灵活处理任务指定不同传感器的情况，使用字典更好
        }

    def _get_default_payload_params(self, sensor_type):
        """根据传感器类型返回默认参数"""
        defaults = {
            'optical': {
                'gsd_m': 0.5,  # 地面分辨率 (米)
                'aperture_m': 0.3,  # 光学口径 (米)
                'sun_elevation_deg': 30  # 太阳高度角 (度)
            },
            'SAR': {
                'wavelength_m': 0.03,  # 波长 (米, X波段)
                'resolution_m': 1.0,  # 分辨率 (米)
                'sar_mode': 'strip',  # 成像模式 (strip/spotlight)
                'slant_range_km': None  # 斜距(千米)
            },
            'infrared': {
                'netd_k': 0.05,  # 噪声等效温差 (K)
                'detector_area_m2': 1e-6,  # 探测器面积 (m²)
                'delta_temp_k': 10,  # 目标与背景温差 (K)
                'scan_mode': 'pushbroom'  # 扫描模式'pushbroom' 或'whiskbroom'
            }
        }
        return defaults.get(sensor_type, {})

    def _calculate_orbit_height(self):
        """从TLE计算轨道高度（千米）"""
        try:
            # 尝试使用skyfield库计算
            from skyfield.api import EarthSatellite, load
            from skyfield.earthlib import earthradius_km

            # 创建卫星对象
            satellite = EarthSatellite(self.tle_line1, self.tle_line2)

            # 获取轨道半长轴
            semi_major_axis_km = satellite.model.a * earthradius_km

            # 估算平均轨道高度（半长轴减去地球半径）
            orbit_height = semi_major_axis_km - earthradius_km

            return orbit_height
        except Exception as e:
            print(f"skyfield 计算轨道高度失败，尝试 sgp4 回退: {e}")
            try:
                # 尝试使用sgp4库计算
                from sgp4.earth_gravity import wgs72
                from sgp4.io import twoline2rv

                satellite = twoline2rv(self.tle_line1, self.tle_line2, wgs72)

                # 计算轨道半长轴（千米）
                semi_major_axis_km = satellite.a * 6378.137

                # 估算平均轨道高度
                orbit_height = semi_major_axis_km - 6378.137  # 减去地球平均半径

                return orbit_height
            except Exception as e:
                # 无法计算，返回默认值
                print(f"sgp4 计算轨道高度也失败，返回默认轨道高度: {e}")
                if self.sensor_type == 'optical':
                    return 600  # 典型光学卫星轨道高度
                else:  # SAR
                    return 700  # 典型SAR卫星轨道高度

    def get_state_at(self, timestamp):
        # print(f"卫星{self.sat_id}尝试获取{timestamp}的状态")
        # print(f"模拟开始时间为{self.simulation_start_time}")
        # 确保不使用早于模拟开始时间的时间
        if hasattr(self, 'simulation_start_time') and timestamp < self.simulation_start_time:
            timestamp = self.simulation_start_time

        # 如果时间戳在时间轴中，直接返回（需要检查naive和aware版本）
        for t in self.state_timeline.keys():
            if t == timestamp:
                # print(f"存在{timestamp}的状态，故返回{self.state_timeline[t]}")
                return copy.deepcopy(self.state_timeline[t])

        # 找出最后一个早于给定时间戳的时间点
        past_timestamps = []
        for t in self.state_timeline.keys():
            if t <= timestamp:
                past_timestamps.append(t)

        if not past_timestamps:
            # 如果没有找到早于给定时间戳的时间点
            if hasattr(self, 'simulation_start_time') and self.simulation_start_time in self.state_timeline:
                # print(f"没有找到早于给定时间的时间点copy自初始状态{self.state_timeline[self.simulation_start_time]}")
                # 使用模拟开始时间的状态
                return copy.deepcopy(self.state_timeline[self.simulation_start_time])
            elif hasattr(self, 'initial_state'):
                # 使用初始状态
                # print(f"没有找到早于给定时间的时间点copy自initial状态{self.initial_state}")
                return copy.deepcopy(self.initial_state)
            else:
                # 创建一个基本状态
                return {
                    'battery_level': getattr(self, 'battery_level', self.initial_battery),
                    'current_storage': getattr(self, 'current_storage', 0),
                    'attitude': getattr(self, 'current_attitude', np.array([1, 0, 0, 0])).copy()
                    if hasattr(self, 'current_attitude') else np.array([1, 0, 0, 0])
                }

        # 使用naive时间戳比较找出最大的过去时间戳
        last_known_time = max(past_timestamps,
                              key=lambda x: x if x.tzinfo is not None else x)
        last_known_state = copy.deepcopy(self.state_timeline[last_known_time])

        # 找出在给定时间戳和最后已知状态之间的所有任务
        tasks_in_interval = []
        last_known_time = last_known_time if last_known_time.tzinfo is not None else last_known_time

        for t in self.tasks:
            start_time = t['start_time'] if t['start_time'].tzinfo is not None else t[
                'start_time']
            if last_known_time < start_time <= timestamp:
                tasks_in_interval.append(t)

        # 返回计算后的状态
        return self._calculate_state_after_tasks(last_known_state, tasks_in_interval,
                                                 last_known_time, timestamp)

    def get_suitable_observation_mode(self, task):
        """为给定任务选择最合适的观测模式"""
        # 如果是点目标(面积很小)
        if task.target_length * task.target_width <= 10000:  # 小于100m x 100m
            if self.sensor_type == 'optical':
                return 'spot_pointing'
            else:  # SAR
                return 'spotlight'

        # 获取目标的长宽比
        aspect_ratio = task.target_length / task.target_width

        if aspect_ratio > 5:  # 细长区域
            # 适合顺轨扫描
            if self.sensor_type == 'optical':
                return 'push_broom'
            else:  # SAR
                return 'stripmap'
        elif task.target_width > self.swath_width:  # 宽度超过单次扫描宽度
            # 需要多次扫描的宽区域
            if self.sensor_type == 'optical':
                return 'side_looking'
            else:  # SAR
                return 'scansar'
        else:
            # 一般区域
            if self.sensor_type == 'optical':
                return 'push_broom'  # 默认光学使用推扫
            else:  # SAR
                return 'stripmap'  # 默认SAR使用条带模式

    def is_free_during(self, start_time, end_time):
        """检查卫星在给定时间段内是否空闲"""
        for occupied_start, occupied_end in self.occupied_time:
            # 判断两个时间段是否重叠
            if start_time < occupied_end and end_time > occupied_start:
                return False
        return True

    def reset_state(self):
        """重置卫星状态以进行新的调度计算"""
        # 重置电池状态 - 更简单明确的逻辑
        if hasattr(self, 'initial_battery') and self.initial_battery is not None:
            # 如果存储了初始电池电量，使用该值
            self.battery_level = self.initial_battery
        else:
            # 如果没有存储初始电量，使用默认值(7容量)
            self.battery_level = self.battery_capacity

        # 确保电池电量在有效范围内
        self.battery_level = max(0, min(self.battery_level, self.battery_capacity))

        # 重置存储状态
        self.current_storage = getattr(self, 'initial_storage', 0)

        # 重置姿态
        self.current_attitude = np.array([1, 0, 0, 0])  # 重置为默认姿态(单位四元数)

        # 重置任务相关属性
        self.occupied_time = []  # 清空任务占用时间段
        self.tasks = []  # 清空已分配的任务记录
        self.last_update_time = None  # 重置上次状态更新时间

        # 重置时间轴
        self.state_timeline = {
            self.simulation_start_time: {
                'battery_level': self.battery_level,
                'current_storage': self.current_storage,
                'attitude': self.current_attitude.copy()
            }
        }

    def calculate_pointing_attitude(self, target_location, time):
        """计算特定时间点指向目标所需的卫星姿态四元数"""
        # 获取卫星在指定时间的位置
        sat_position = self.get_position_at(time)
        if sat_position is None or 'latitude' not in sat_position:
            # 无法获取卫星位置，返回默认姿态
            return np.array([1, 0, 0, 0])
        # 从经纬度坐标转换为空间直角坐标系
        sat_lat, sat_lon = sat_position['latitude'], sat_position['longitude']
        sat_height = sat_position.get('height', 500)  # 默认高度500km
        target_lat, target_lon = target_location
        # 将经纬度转换为地心惯性坐标系(ECI)中的向量
        R_earth = 6371.0  # 地球半径(km)

        # 卫星位置向量
        sat_r = R_earth + sat_height  # 卫星到地心距离
        sat_lat_rad = math.radians(sat_lat)
        sat_lon_rad = math.radians(sat_lon)

        sat_x = sat_r * math.cos(sat_lat_rad) * math.cos(sat_lon_rad)
        sat_y = sat_r * math.cos(sat_lat_rad) * math.sin(sat_lon_rad)
        sat_z = sat_r * math.sin(sat_lat_rad)
        sat_pos = np.array([sat_x, sat_y, sat_z])

        # 目标位置向量
        target_lat_rad = math.radians(target_lat)
        target_lon_rad = math.radians(target_lon)

        target_x = R_earth * math.cos(target_lat_rad) * math.cos(target_lon_rad)
        target_y = R_earth * math.cos(target_lat_rad) * math.sin(target_lon_rad)
        target_z = R_earth * math.sin(target_lat_rad)
        target_pos = np.array([target_x, target_y, target_z])

        # 计算从卫星到目标的指向向量
        pointing_vector = target_pos - sat_pos
        pointing_vector = pointing_vector / np.linalg.norm(pointing_vector)  # 归一化

        # 计算卫星机体坐标系到指向坐标系的旋转四元数
        # 假设卫星标准姿态为z轴指向地心
        nadir_vector = -sat_pos / np.linalg.norm(sat_pos)  # 指向地心的单位向量

        # 计算旋转轴和旋转角
        rotation_axis = np.cross(nadir_vector, pointing_vector)

        # 如果旋转轴接近零向量，表示两向量几乎平行
        if np.linalg.norm(rotation_axis) < 1e-6:
            if np.dot(nadir_vector, pointing_vector) > 0:  # 同向
                return np.array([1, 0, 0, 0])  # 不需要旋转
            else:  # 反向
                # 需要180度旋转，选择卫星速度方向的垂直轴
                # 简化实现，使用x轴
                return np.array([0, 1, 0, 0])  # 绕x轴旋转180度

        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)  # 归一化旋转轴

        # 计算旋转角度
        cos_angle = np.dot(nadir_vector, pointing_vector)
        cos_angle = max(min(cos_angle, 1.0), -1.0)  # 确保在[-1,1]范围内
        angle = math.acos(cos_angle)

        # 构建四元数 [cos(angle/2), sin(angle/2)*axis_x, sin(angle/2)*axis_y, sin(angle/2)*axis_z]
        half_angle = angle / 2.0
        q_w = math.cos(half_angle)
        q_x = rotation_axis[0] * math.sin(half_angle)
        q_y = rotation_axis[1] * math.sin(half_angle)
        q_z = rotation_axis[2] * math.sin(half_angle)
        return np.array([q_w, q_x, q_y, q_z])

    def update_state_after(self, timestamp, new_state):
        """更新指定时间戳之后的所有状态"""
        # 确保时间戳的时区一致性
        timestamp = timestamp if timestamp.tzinfo is not None else timestamp

        # 获取所有未来的时间戳并排序
        future_timestamps = []
        for t in self.state_timeline.keys():
            t = t if t.tzinfo is not None else t
            if t > timestamp:
                future_timestamps.append(t)

        future_timestamps.sort(key=lambda x: x if x.tzinfo is not None else x)

        if not future_timestamps:
            return  # 没有未来的时间戳需要更新

        current_state = copy.deepcopy(new_state)
        current_time = timestamp

        for next_time in future_timestamps:
            next_time = next_time if next_time.tzinfo is not None else next_time

            # 找出在当前时间和下一个时间戳之间的所有任务
            tasks_in_interval = []
            for t in self.tasks:
                start_time = t['start_time'] if t['start_time'].tzinfo is not None else t[
                    'start_time']
                if current_time < start_time <= next_time:
                    tasks_in_interval.append(t)

            # 计算下一个时间戳的状态
            next_state = self._calculate_state_after_tasks(current_state, tasks_in_interval,
                                                           current_time, next_time)

            # 更新时间轴
            self.state_timeline[next_time] = next_state

            # 更新当前状态和时间
            current_state = copy.deepcopy(next_state)
            current_time = next_time

    def _find_tasks_between(self, start_time, end_time):
        """找出两个时间点之间的所有任务"""
        # 确保时间戳的时区一致性
        if start_time.tzinfo is not None:
            start_time = start_time
        if end_time.tzinfo is not None:
            end_time = end_time

        tasks_between = []
        for task in self.tasks:
            # 确保任务时间也是时区一致的
            task_start = task['start_time']
            task_end = task['end_time']

            if task_start.tzinfo is not None:
                task_start = task_start
            if task_end.tzinfo is not None:
                task_end = task_end

            # 检查任务是否在时间区间内
            if (start_time <= task_start < end_time or
                    start_time < task_end <= end_time or
                    (task_start <= start_time and task_end >= end_time)):
                tasks_between.append(task)

        return tasks_between

    def _calculate_state_after_tasks(self, initial_state, tasks, start_time, end_time):
        """计算执行一系列任务后的状态"""

        # 复制初始状态
        state = copy.deepcopy(initial_state)
        # print(f"真初始状态{state}")
        original_battery = state['battery_level']

        # 按时间顺序排序任务
        sorted_tasks = sorted(tasks, key=lambda t: t['start_time'])

        current_time = start_time

        # 处理每个任务
        for task in sorted_tasks:
            # 确保任务时间的时区一致性
            task_start = task['start_time']
            task_end = task['end_time']

            # 先处理当前时间到任务开始时间之间的自然状态变化（如充电）
            if current_time < task_start:
                self._update_natural_state(state, current_time, task_start)
                current_time = task_start

            # 获取任务开始前的电池状态用于日志
            battery_before_task = state['battery_level']
            battery_percent_before = (battery_before_task / self.battery_capacity) * 100

            # 判断是否为日照期
            is_eclipse = True  # 默认为阴影期
            for charge_start, charge_end in self.charging_windows:
                # 确保充电窗口时间的时区一致性
                if charge_start.tzinfo is not None:
                    charge_start = charge_start
                if charge_end.tzinfo is not None:
                    charge_end = charge_end

                if max(task_start, charge_start) < min(task_end, charge_end):
                    is_eclipse = False
                    break

            # 计算任务能耗和存储使用
            energy_consumption = self.calculate_energy_consumption(
                task['task_object'], task['observation_time'], is_eclipse)

            # 更新电池状态
            state['battery_level'] -= energy_consumption

            # 获取任务后的电池状态用于日志
            battery_after_task = state['battery_level']
            battery_percent_after = (battery_after_task / self.battery_capacity) * 100
            battery_change = battery_after_task - battery_before_task
            battery_percent_change = battery_percent_after - battery_percent_before

            # 确保每次更新后电池电量不低于0
            state['battery_level'] = max(state['battery_level'], 0.0)
            state['current_storage'] = min(state['current_storage'], self.data_storage)
            # 更新存储状态（如果任务包含存储信息）
            if 'storage_added' in task:
                state['current_storage'] += task['storage_added']
                # 确保存储量不超过容量
                state['current_storage'] = min(state['current_storage'], self.data_storage)

            # 更新姿态
            if 'attitude_after' in task:
                state['attitude'] = task['attitude_after'].copy()

            # 更新当前时间
            current_time = task_end

        # # 处理任务结束后到结束时间的自然状态变化
        # if current_time < end_time:
        #     self._update_natural_state(state, current_time, end_time)

        # 确保状态在有效范围内
        state['battery_level'] = min(state['battery_level'], self.battery_capacity)
        state['battery_level'] = max(state['battery_level'], 0)
        state['current_storage'] = max(state['current_storage'], 0)
        state['current_storage'] = min(state['current_storage'], self.data_storage)

        # 最终电池状态变化
        final_battery_change = state['battery_level'] - original_battery
        final_percent_change = (final_battery_change / self.battery_capacity) * 100

        return state

    def calculate_storage(self, task, observation_seconds):
        # 计算区域大小和分辨率
        if isinstance(observation_seconds, timedelta):
            # 若为timedelta，转换为总秒数后取整
            observation_seconds = observation_seconds.total_seconds()
        area = task.target_length * task.target_width
        pixel_count = area / self.resolution_capability
        mul = observation_seconds / 4
        # 计算数据量（以GB为单位）
        if self.sensor_type == 'optical':
            bits_per_pixel = 24  # 彩色图像（RGB）
        elif self.sensor_type == 'sar' or 'SAR':  # SAR
            bits_per_pixel = 64
        else:
            bits_per_pixel = 16
        # 数据量 = 像素数 × 每像素比特数 / 8(转换为字节) / 1073741824(转换为GB)
        storage_increase = (pixel_count * bits_per_pixel * mul) / 8 / 1073741824
        return storage_increase

    def add_task(self, task, start_time, end_time, observation_time=None):
        """向卫星添加任务"""
        if not self.is_free_during(start_time, end_time):
            return False

        # 确保时间戳的时区一致性
        start_time = start_time if start_time.tzinfo is not None else start_time
        end_time = end_time if end_time.tzinfo is not None else end_time

        # 获取任务开始前的状态

        state_before_task = self.get_state_at(start_time)
        # print(f"{self.sat_id}在任务{task.task_id}前状态为{state_before_task}")
        # 计算机动时间
        maneuver_duration = self.calculate_maneuver_duration(task, start_time)

        # 如果没有提供观测时间，则计算
        if observation_time is None:
            observation_time = self.get_observation_time(task, start_time)
        # 总持续时间应该小于时间窗口
        # 检查 maneuver_duration 和 observation_time 的类型，并适当处理
        if isinstance(maneuver_duration, timedelta):
            maneuver_seconds = maneuver_duration.total_seconds()
        else:
            maneuver_seconds = maneuver_duration

        if isinstance(observation_time, timedelta):
            observation_seconds = observation_time.total_seconds()
        else:
            observation_seconds = observation_time

        total_duration = timedelta(seconds=maneuver_seconds + observation_seconds)
        observation_end_time = start_time + total_duration
        if observation_end_time > end_time:
            return False

        # 判断是否为日照期
        is_eclipse = True
        for charge_start, charge_end in self.charging_windows:
            charge_start = charge_start if charge_start.tzinfo is not None else charge_start
            charge_end = charge_end if charge_end.tzinfo is not None else charge_end
            if max(start_time, charge_start) < min(observation_end_time, charge_end):
                is_eclipse = False
                break

        # 计算能量消耗
        energy_consumption = self.calculate_energy_consumption(task, observation_time, is_eclipse)

        # 检查电池电量是否足够
        battery_before = state_before_task['battery_level']
        battery_percent_before = (battery_before / self.battery_capacity) * 100
        if battery_before < energy_consumption:
            return False

        # 数据量 = 像素数 × 每像素比特数 / 8(转换为字节) / 1073741824(转换为GB)
        storage_increase = self.calculate_storage(task, observation_seconds)
        efficiency = 1.0
        storage_increase *= efficiency

        if state_before_task['current_storage'] + storage_increase > self.data_storage:
            return False

        # 创建任务后的状态
        state_after_task = copy.deepcopy(state_before_task)
        # 确保电池电量正确减少
        state_after_task['battery_level'] -= energy_consumption

        # 显示电池变化
        battery_after = state_after_task['battery_level']
        battery_percent_after = (battery_after / self.battery_capacity) * 100
        battery_change = battery_after - battery_before
        battery_percent_change = battery_percent_after - battery_percent_before

        # 更新存储
        state_after_task['current_storage'] += storage_increase
        # 确保电池电量不会低于0
        state_after_task['battery_level'] = max(state_after_task['battery_level'], 0.0)
        # 确保电池电量不会超过容量
        state_after_task['battery_level'] = min(state_after_task['battery_level'], self.battery_capacity)

        # 更新姿态
        previous_attitude = state_before_task['attitude'].copy()
        if task.task_type != '移动目标':
            task.target_attitude = self.calculate_pointing_attitude(task.target_location, start_time)
        else:
            task.target_attitude = random.choice(self.boundary_quaternions)
        state_after_task['attitude'] = task.target_attitude
        # 添加到占用时间
        self.occupied_time.append((start_time, observation_end_time))
        # print(f"add_task中{observation_seconds}")
        # 创建任务记录
        task_record = {
            'task_id': task.task_id,
            'task_object': task,  # 保存任务对象引用以便后续计算
            'start_time': start_time,
            'end_time': observation_end_time,
            'observation_time': observation_seconds,
            'maneuver_duration': maneuver_duration,
            'energy_consumed': energy_consumption,
            'storage_added': storage_increase,
            'battery_before_task': state_before_task['battery_level'],
            'battery_after_task': state_after_task['battery_level'],
            'battery_percent_before': battery_percent_before,
            'battery_percent_after': battery_percent_after,
            'attitude_before': previous_attitude,
            'attitude_after': task.target_attitude
        }

        # 记录任务
        self.tasks.append(task_record)

        # 先更新任务开始时间的状态，再更新任务结束时间的状态
        self.state_timeline[start_time] = copy.deepcopy(state_before_task)
        self.state_timeline[observation_end_time] = copy.deepcopy(state_after_task)

        # 更新时间轴中结束时间之后的所有状态
        self.update_state_after(observation_end_time, state_after_task)
        return True

    def calculate_energy_consumption(self, task, duration, is_eclipse=False):
        """计算任务能量消耗（以Wh为单位）- 只包括任务特定消耗（机动和成像）"""
        # 确保duration是timedelta类型
        if not isinstance(duration, timedelta):
            duration = timedelta(seconds=duration)

        # 分解总持续时间
        total_seconds = duration.total_seconds()
        total_hours = total_seconds / 3600  # 转换为小时

        # 计算机动和成像时间
        # (这部分逻辑与之前修改的一致，确保机动时间合理)
        maneuver_seconds = 0
        imaging_seconds = 0

        if hasattr(task, 'maneuver_duration') and task.maneuver_duration is not None:
            if isinstance(task.maneuver_duration, timedelta):
                maneuver_seconds = task.maneuver_duration.total_seconds()
            elif isinstance(task.maneuver_duration, (int, float)):
                maneuver_seconds = float(task.maneuver_duration)

            # 确保机动时间不超过总时间且不为负
            maneuver_seconds = min(max(maneuver_seconds, 0), total_seconds)
            imaging_seconds = total_seconds - maneuver_seconds
        else:
            # 如果没有指定机动时间，使用合理的默认值
            min_maneuver_time = 10  # 最小机动时间(秒)
            default_maneuver_ratio = 0.2  # 默认机动时间比例

            maneuver_seconds = max(min_maneuver_time, total_seconds * default_maneuver_ratio)
            # 确保机动时间不超过总时间
            maneuver_seconds = min(maneuver_seconds, total_seconds)

            imaging_seconds = total_seconds - maneuver_seconds

        # 转换为小时
        maneuver_hours = maneuver_seconds / 3600
        imaging_hours = imaging_seconds / 3600

        # 计算任务特定能耗（机动和成像），不包括空闲消耗
        # 根据日照/日食期选择机动功率
        maneuver_power = self.eclipse_powers.get('maneuver', 700) if is_eclipse else self.sunlight_powers.get(
            'maneuver',
            700)

        # 获取传感器类型，默认光学
        sensor_type = self.sensor_type

        # 获取成像功率，如果sensor_type不存在，默认使用光学的功率
        imaging_power = self.imaging_powers.get(sensor_type, self.imaging_powers.get('optical', 500))

        # 计算能耗 (Wh)
        maneuver_energy = maneuver_hours * maneuver_power
        imaging_energy = imaging_hours * imaging_power

        # 总任务特定消耗
        total_consumption = maneuver_energy + imaging_energy

        # 应用观测模式效率因子 (这部分逻辑与之前修改的一致)
        observation_mode = self.get_suitable_observation_mode(task)
        mode_efficiency = 1.0
        # 效率因子影响能耗 (效率低的模式耗能更多)
        # 确保 total_consumption 不为零，避免除零错误或乘以/除以无穷大
        if total_consumption > 0:
            energy_consumption = total_consumption / mode_efficiency
        else:
            energy_consumption = 0  # 如果机动和成像能耗都为0，总消耗也为0

        # 确保至少有最小能耗 (对于非零时长的任务)
        min_energy = 5  # 最小能耗，避免完全免费的任务
        if total_seconds > 0:
            energy_consumption = max(energy_consumption, min_energy)
        else:
            energy_consumption = 0  # 0时长的任务消耗为0

        return energy_consumption

    def _update_natural_state(self, state, from_time, to_time):
        """更新自然状态变化（充电、放电等）"""
        # 确保时间戳的时区一致性
        if from_time.tzinfo is not None:
            from_time = from_time
        if to_time.tzinfo is not None:
            to_time = to_time

        # 确保不使用早于模拟开始时间的时间
        if hasattr(self, 'simulation_start_time') and from_time < self.simulation_start_time:
            from_time = self.simulation_start_time

        # 计算时间差
        time_diff = to_time - from_time
        total_seconds = time_diff.total_seconds()

        # 确保时间差为正数
        if total_seconds <= 0:
            return state

        # 限制最大更新时间为24小时，防止异常值
        max_hours = 24
        if total_seconds > max_hours * 3600:
            total_seconds = max_hours * 3600
            to_time = from_time + timedelta(hours=max_hours)

        # 计算总时间（小时）
        total_time_hours = total_seconds / 3600
        original_battery = state['battery_level']
        # print(f"初始状态{state}")
        # 计算充电时间
        charging_time = timedelta(seconds=0)
        for charge_start, charge_end in self.charging_windows:
            # 确保充电窗口时间的时区一致性
            if charge_start.tzinfo is not None:
                charge_start = charge_start
            if charge_end.tzinfo is not None:
                charge_end = charge_end
            overlap_start = max(from_time, charge_start)
            overlap_end = min(to_time, charge_end)
            if overlap_start < overlap_end:
                charging_time += (overlap_end - overlap_start)

        charging_hours = charging_time.total_seconds() / 3600
        eclipse_hours = total_time_hours - charging_hours

        # 充电期间的电量变化 - 使用充电率
        if charging_hours > 0:
            # 日照期，使用充电率但减去空闲消耗
            charge_rate = self.sunlight_powers['charge']  # 充电功率（W）
            idle_consumption = self.sunlight_powers['idle']  # 空闲消耗（W）

            # 净充电率 = 充电率 - 空闲消耗
            net_charge_rate = charge_rate - idle_consumption
            charge_amount = net_charge_rate * charging_hours  # Wh

            # 添加充电但不超过容量
            original_level = state['battery_level']
            state['battery_level'] = min(state['battery_level'] + charge_amount, self.battery_capacity)
            actual_charge = state['battery_level'] - original_level

        # 放电期间的电量变化 - 使用idle功率
        if eclipse_hours > 0:
            # 日食期，只有放电（空闲消耗）
            discharge_rate = self.eclipse_powers['idle']  # 空闲消耗（W）
            discharge_amount = discharge_rate * eclipse_hours  # Wh

            # 减去放电但不低于0
            original_level = state['battery_level']
            state['battery_level'] = max(state['battery_level'] - discharge_amount, 0)
            actual_discharge = original_level - state['battery_level']

        # # 处理数据下行
        # total_downlink = 0
        # for downlink_start, downlink_end in self.downlink_windows:
        #     # 确保下行窗口时间的时区一致性
        #     if downlink_start.tzinfo is not None:
        #         downlink_start = downlink_start
        #     if downlink_end.tzinfo is not None:
        #         downlink_end = downlink_end
        #
        #     overlap_start = max(from_time, downlink_start)
        #     overlap_end = min(to_time, downlink_end)
        #     if overlap_start < overlap_end:
        #         downlink_time = (overlap_end - overlap_start).total_seconds()
        #         downlink_rate = 0.1  # 每秒0.1GB
        #         downlink_capacity = downlink_rate * downlink_time
        #         actual_downlink = min(state['current_storage'], downlink_capacity)
        #         state['current_storage'] -= actual_downlink
        #         total_downlink += actual_downlink

        state['battery_level'] = min(state['battery_level'], self.battery_capacity)
        state['battery_level'] = max(state['battery_level'], 0.0)
        print(f"{self.sat_id}自然{state}")

        return state

    def calculate_maneuver_duration(self, task, time):
        """计算姿态机动所需的时间"""
        # 首先计算指向任务目标所需的姿态
        target_attitude = self.calculate_pointing_attitude(task.target_location,
                                                           time)

        # 将计算出的姿态四元数设置为任务的目标姿态
        if task.target_attitude is None:
            task.target_attitude = target_attitude

        # 计算两个姿态之间的角度
        q1 = self.current_attitude
        q2 = task.target_attitude

        try:
            from scipy.spatial.transform import Rotation
            r1 = Rotation.from_quat([q1[1], q1[2], q1[3], q1[0]])  # [x,y,z,w]
            r2 = Rotation.from_quat([q2[1], q2[2], q2[3], q2[0]])

            # 计算旋转角度(度)
            angle_deg = (r2 * r1.inv()).magnitude() * 180 / np.pi
        except Exception as e:
            # 简化计算
            print(f"scipy 姿态角计算失败，使用简化计算: {e}")
            dot_product = np.abs(np.dot(q1, q2))
            angle_deg = 2 * np.arccos(min(1, dot_product)) * 180 / np.pi

        # 考虑卫星姿态控制系统的物理限制
        max_slew_rate = self.max_slew_rate  # 最大转动速率(度/秒)
        max_acceleration = 0.5  # 最大角加速度(度/秒²)

        # 计算加速到最大速率所需的时间和角度
        accel_time = max_slew_rate / max_acceleration  # 秒
        accel_angle = 0.5 * max_acceleration * accel_time ** 2  # 度

        # 总角度
        if angle_deg <= 2 * accel_angle:
            # 角度太小，来不及加速到最大速率
            # 使用梯形速度曲线
            maneuver_time = 2 * np.sqrt(angle_deg / max_acceleration)
        else:
            # 有足够角度达到最大速率
            # 匀速部分角度
            uniform_angle = angle_deg - 2 * accel_angle
            # 匀速时间
            uniform_time = uniform_angle / max_slew_rate
            # 总时间 = 加速时间 + 匀速时间 + 减速时间
            maneuver_time = 2 * accel_time + uniform_time

        # 考虑控制系统启动和稳定时间
        settling_time = 2.0  # 秒
        total_seconds = maneuver_time + settling_time

        # 设置最小机动时间
        min_maneuver_time = 3.0  # 秒
        return timedelta(seconds=max(total_seconds, min_maneuver_time))

    def get_max_observation_area(self, mode=None):
        """获取卫星在特定观测模式下能覆盖的最大区域面积"""
        if mode is None:
            # 返回所有模式的最大值
            max_area = 0
            for mode_name, mode_info in self.observation_modes.items():
                if 'max_area' in mode_info:
                    max_area = max(max_area, mode_info['max_area'])
                elif 'max_width' in mode_info:
                    # 对于扫描类模式，估算最大面积
                    # 假设长度方向不受限制，最大面积由宽度决定
                    width = mode_info['max_width']
                    # 假设轨道周期为90分钟(典型LEO卫星)
                    orbit_period_seconds = 90 * 60
                    # 假设单轨道最多可以连续观测5分钟
                    max_observation_time = 5 * 60
                    # 估算最大长度(地面距离)
                    max_length = (max_observation_time / orbit_period_seconds) * 2 * np.pi * 6371000  # 地球周长
                    area = width * max_length
                    max_area = max(max_area, area)
            return max_area
        else:
            # 返回指定模式的最大区域
            if mode in self.observation_modes:
                mode_info = self.observation_modes[mode]
                if 'max_area' in mode_info:
                    return mode_info['max_area']
                elif 'max_width' in mode_info:
                    width = mode_info['max_width']
                    # 估算最大长度
                    max_observation_time = 5 * 60  # 5分钟
                    orbit_period_seconds = 90 * 60  # 90分钟
                    max_length = (max_observation_time / orbit_period_seconds) * 2 * np.pi * 6371000
                    return width * max_length

            # 默认值(10km x 10km)
            return 10000 * 10000

    import random
    from datetime import timedelta
    def _calculate_orbit_params(self, time):
        """从TLE计算轨道高度(km)和速度(m/s)"""
        t = self.ts.from_datetime(time)  # 将datetime转换为skyfield的Time对象
        geocentric = self.satellite.at(t)
        position_km = geocentric.position.km
        velocity_kms = geocentric.velocity.km_per_s

        altitude_km = np.linalg.norm(position_km) - 6371  # 地球半径6371km
        satellite_speed_mps = np.linalg.norm(velocity_kms) * 1000  # 转为m/s
        return altitude_km, satellite_speed_mps

    def get_observation_time(self, task, observation_time):
        """
        计算观测给定任务所需的时间
        参数:
            task: 任务对象，需包含task_type、target_length、target_width属性
            observation_time: datetime对象，指定观测时间
        返回:
            timedelta对象，表示观测所需时间
        """
        if task.task_type == '移动目标':
            return timedelta(seconds=random.randint(3 * 60, 5 * 60))

        # 计算轨道参数
        altitude_km, speed_mps = self._calculate_orbit_params(observation_time)
        # 合并参数
        params = {
            'altitude_km': altitude_km,
            'satellite_speed_mps': speed_mps,
            'target_length_km': self.swath_width,
            'target_width_km': self.swath_width
        }
        params.update(self.payload_params)

        if self.sensor_type == 'optical':
            # 可见光模型
            exposure_time = (params['gsd_m'] ** 2) / (params['aperture_m'] * params['sun_elevation_deg']) * 0.3 * 25
            coverage_time = (self.swath_width * 1) / (speed_mps * (self.swath_width / altitude_km)) * 25
            total_seconds = max(exposure_time, coverage_time)

        elif self.sensor_type == 'SAR':
            # SAR模型
            slant_range = params.get('slant_range_km', altitude_km)
            if slant_range is None:
                slant_range = altitude_km
            synth_time = (params['wavelength_m'] * slant_range * 1000) / (speed_mps * params['resolution_m']) * 3
            total_seconds = synth_time * 1.2 if params['sar_mode'] == 'spotlight' else synth_time

        elif self.sensor_type == 'infrared':
            # 红外模型
            integration_time = (params['netd_k'] ** 2) / (params['detector_area_m2'] * params['delta_temp_k']) * 1e3
            total_seconds = integration_time * (self.swath_width / 5) if params[
                                                                             'scan_mode'] == 'whiskbroom' else integration_time * 2
        else:
            raise ValueError(f"未知传感器类型: {self.sensor_type}")

        return timedelta(seconds=round(total_seconds, 2))

    def __str__(self):
        """返回卫星描述信息"""
        tasks_count = len(self.tasks)
        self.battery_level = min(self.battery_level, self.battery_capacity)
        self.battery_level = max(self.battery_level, 0)
        capacity_percentage = self.battery_level / self.battery_capacity * 100
        storage_percentage = self.current_storage / self.data_storage * 100

        return (f"Satellite {self.sat_id} ({self.sensor_type}):\n"
                f"  轨道高度: {self.orbit_height:.1f} km\n"
                f"  分辨率能力: {self.resolution_capability} m\n"
                f"  任务数: {tasks_count}\n"
                f"  电量: {capacity_percentage:.1f}%\n"
                f"  存储: {storage_percentage:.1f}%\n"
                f"  扫描宽度: {self.swath_width:.1f} km\n"
                f"  最大侧摆角: {self.max_roll_angle} 度")

    def get_position_at(self, time):
        """获取卫星在指定时间的位置（经纬度和高度）"""
        try:
            # 尝试使用skyfield库计算
            from skyfield.api import EarthSatellite, load

            # 创建卫星对象
            satellite = EarthSatellite(self.tle_line1, self.tle_line2)

            # 加载时间
            ts = load.timescale()
            t = ts.from_datetime(time)

            # 计算位置
            geocentric = satellite.at(t)
            subpoint = geocentric.subpoint()

            # 返回经纬度和高度
            return {
                'latitude': subpoint.latitude.degrees,
                'longitude': subpoint.longitude.degrees,
                'height': subpoint.elevation.km,
                'velocity': np.linalg.norm(geocentric.velocity.km_per_s)
            }
        except Exception as e:
            print(f"skyfield 获取卫星状态失败，尝试 sgp4 回退: {e}")
            try:
                # 尝试使用sgp4库计算
                from sgp4.earth_gravity import wgs72
                from sgp4.io import twoline2rv
                import datetime

                satellite = twoline2rv(self.tle_line1, self.tle_line2, wgs72)

                # 计算从历元到目标时间的分钟数
                epoch = satellite.epoch
                target_time = time
                time_diff = (target_time - epoch).total_seconds() / 60.0

                # 计算位置和速度
                position, velocity = satellite.propagate(
                    time.year, time.month, time.day,
                    time.hour, time.minute, time.second
                )

                # 将直角坐标转换为地理坐标
                from sgp4.ext import rv2coe

                # 计算轨道要素
                mu = wgs72.mu  # 地球引力常数
                p, a, ecc, incl, node, argp, nu, m, arglat, truelon, lonper = rv2coe(
                    position, velocity, mu
                )

                # 简化，返回近似值
                return {
                    'latitude': np.degrees(nu),  # 这只是个近似，实际需要更复杂的转换
                    'longitude': np.degrees(node),  # 近似值
                    'height': np.linalg.norm(position) - 6378.137,  # 近似高度
                    'velocity': np.linalg.norm(velocity)
                }
            except Exception as e:
                # 无法计算，返回默认值
                return {
                    'latitude': 0,
                    'longitude': 0,
                    'height': self.orbit_height,
                    'velocity': 7.0  # 典型LEO卫星速度 km/s
                }


class SatelliteCluster:
    def __init__(self, cluster_name):
        self.cluster_name = cluster_name
        self.satellites = []

    def add_satellite(self, satellite):
        """添加卫星，只要卫星的cluster_names包含本星簇名称即可"""
        if self.cluster_name in satellite.cluster_names:
            self.satellites.append(satellite)
            return True
        return False

    def get_satellites(self):
        return self.satellites


def subtract_occupied_windows(available_windows, occupied_windows):
    """从可用时间窗口中减去已占用的时间窗口"""
    result = []

    for avail_start, avail_end in available_windows:
        current_start = avail_start

        for occ_start, occ_end in sorted(occupied_windows):
            # 如果占用窗口在当前片段之前结束，忽略
            if occ_end <= current_start:
                continue

            # 如果占用窗口在当前片段之后开始，当前片段完整保留
            if occ_start >= avail_end:
                break

            # 如果占用窗口与当前片段有重叠，切分片段
            if occ_start > current_start:
                result.append((current_start, occ_start))

            # 更新当前起点
            current_start = max(current_start, occ_end)

            # 如果当前起点已经超过了可用窗口结束，跳出
            if current_start >= avail_end:
                break

        # 添加最后一个片段
        if current_start < avail_end:
            result.append((current_start, avail_end))

    return result


def quaternion_to_euler(q, roll_limit=(-180, 180), pitch_limit=(-90, 90), yaw_limit=(-180, 180)):
    """四元数转欧拉角（roll, pitch, yaw，以度为单位），并对滚转角、俯仰角和偏航角进行限制"""
    # 确保q是(w, x, y, z)格式
    if len(q) != 4:
        raise ValueError("四元数必须是长度为4的数组")

    w, x, y, z = q

    # 计算roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # 计算pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = np.pi / 2 * np.sign(sinp)  # 90度，如果sinp超出范围
    else:
        pitch = np.arcsin(sinp)

    # 计算yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    # 转换为度
    roll = np.degrees(roll)
    pitch = np.degrees(pitch)
    yaw = np.degrees(yaw)

    # 对滚转角、俯仰角和偏航角进行限制
    roll = np.clip(roll, roll_limit[0], roll_limit[1])
    pitch = np.clip(pitch, pitch_limit[0], pitch_limit[1])
    yaw = np.clip(yaw, yaw_limit[0], yaw_limit[1])

    return roll, pitch, yaw


# 卫星调度器类
class SatelliteScheduler:
    def __init__(self, tasks, satellites, start_time, end_time, algorithm='genetic', priority_gravity=3.0,
                 balance_gravity=0.3, completed_gravity=0.5, ):
        self.tasks = tasks
        self.satellites = satellites
        self.start_time = start_time if start_time.tzinfo is not None else start_time
        self.end_time = end_time if end_time.tzinfo is not None else end_time
        self.algorithm = algorithm  # 调度算法: 'greedy', 'genetic', 'ant_colony'
        # 创建星簇
        self.sat_clusters = self._create_clusters()
        # 预处理任务和卫星
        for sat in self.satellites:
            sat.simulation_start_time = self.start_time
            # 确保在 simulation_start_time 处有初始状态记录
        self._preprocess()
        self.priority_gravity = priority_gravity
        self.balance_gravity = balance_gravity
        self.completed_gravity = completed_gravity

    def _get_suitable_satellites(self, task):
        """返回任务指定星簇内的所有卫星"""
        suitable_satellites = []
        for cluster in self.sat_clusters:
            # 检查星簇是否在任务的cluster_names中
            if cluster.cluster_name in task.cluster_names:
                suitable_satellites.extend(cluster.get_satellites())
        return suitable_satellites

    def _create_clusters(self):
        """创建所有唯一的星簇"""
        # 收集所有唯一的cluster_name
        all_cluster_names = set()
        for satellite in self.satellites:
            all_cluster_names.update(satellite.cluster_names)

        # 为每个唯一cluster_name创建星簇
        clusters = {}
        for cluster_name in all_cluster_names:
            clusters[cluster_name] = SatelliteCluster(cluster_name)

        # 将卫星添加到所有相关的星簇中
        for satellite in self.satellites:
            for cluster_name in satellite.cluster_names:
                if cluster_name in clusters:
                    clusters[cluster_name].add_satellite(satellite)

        return list(clusters.values())

    def _genetic_algorithm(self, population_size=30, max_generations=10,
                           crossover_rate=0.8, mutation_rate=0.2,
                           elite_size=3, tournament_size=3):
        """使用遗传算法进行任务调度"""
        # 创建遗传算法优化器
        ga = GeneticAlgorithm(
            tasks=self.tasks,
            sat_clusters=self.sat_clusters,
            simulation_start_time=self.start_time,
            simulation_end_time=self.end_time,
            priority_gravity=self.priority_gravity, balance_gravity=self.balance_gravity,
            completed_gravity=self.completed_gravity
        )

        # 运行算法
        schedule = ga.solve(
            population_size=population_size,
            max_generations=10,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            elite_size=elite_size,
            tournament_size=tournament_size
        )

        if not schedule:
            print("遗传算法未能找到可行的调度方案，尝试使用贪心算法作为备选")
            schedule = self._greedy_schedule()

        return schedule

    def solve(self, algorithm=None, num_iterations=30, num_ants=30, evaporation_rate=0.05,
              alpha=1.5, beta=2.5, q0=0.7, elite_ants=3, local_search=True,
              population_size=50, max_generations=30, crossover_rate=0.8,
              mutation_rate=0.2, elite_size=5, tournament_size=3):
        """调度任务"""
        # 允许覆盖默认算法
        if algorithm:
            self.algorithm = algorithm

        # 调用相应的调度算法
        if self.algorithm == 'greedy':
            schedule = self._greedy_schedule()
        elif self.algorithm == 'genetic':
            schedule = self._genetic_algorithm(
                population_size=population_size,
                max_generations=max_generations,
                crossover_rate=crossover_rate,
                mutation_rate=mutation_rate,
                elite_size=elite_size,
                tournament_size=tournament_size
            )
        elif self.algorithm == 'ant_colony':
            schedule = self._ant_colony_optimization(
                num_iterations=num_iterations,
                num_ants=num_ants,
                evaporation_rate=evaporation_rate,
                alpha=alpha,
                beta=beta,
                q0=q0,
                local_search=local_search,
            )
        else:
            print(f"未知算法 '{self.algorithm}'，使用默认的蚁群优化算法")
            schedule = self._ant_colony_optimization(
                num_iterations=num_iterations,
                num_ants=num_ants,
                evaporation_rate=evaporation_rate,
                alpha=alpha,
                beta=beta,
                q0=q0,
                local_search=local_search
            )

        return schedule

    def _greedy_schedule(self):
        """使用贪心算法进行任务调度"""
        # 创建贪心算法优化器
        greedy = GreedyAlgorithm(self.tasks, self.sat_clusters,
                                 self.start_time, self.end_time)

        # 运行算法
        schedule = greedy.solve()

        return schedule

    def _ant_colony_optimization(self, num_iterations=100, num_ants=20, evaporation_rate=0.1,
                                 alpha=1.0, beta=2.0, q0=0.5, local_search=True):
        """使用蚁群优化算法进行任务调度"""
        # 创建蚁群优化器
        aco = AntColonyOptimizer(self.tasks, self.sat_clusters, simulation_start_time=self.start_time,
                                 simulation_end_time=self.end_time)

        # 运行算法
        schedule = aco.solve(
            evaporation_rate=evaporation_rate,
            alpha=alpha,
            beta=beta,
        )

        return schedule

    def merge_subtasks(self, solution):
        """
        改进版合并函数，精确计算连续时间段的资源消耗

        返回结构：
        {
            "TASK_001": {
                "SAT_001": {
                    "2023-01-01 08:00:00,2023-01-01 10:00:00": {
                        "battery_cost": 根据首尾电量计算的值,
                        "storage_added": 根据首尾存储计算的值,
                        ...
                    }
                }
            }
        }
        """
        merged_result = {}

        # 第一步：按父任务ID分组
        task_groups = {}
        for task in solution:
            task_id = task['parent_id'] if task['parent_id'] is not None else task['task_id']
            if task_id not in task_groups:
                task_groups[task_id] = []
            task_groups[task_id].append(task)

        # 第二步：处理每个任务组
        for task_id, tasks in task_groups.items():
            satellite_data = {}

            # 按卫星ID分组
            sat_groups = {}
            for task in tasks:
                sat_id = task['satellite_id']
                if sat_id not in sat_groups:
                    sat_groups[sat_id] = []
                sat_groups[sat_id].append(task)

            # 处理每个卫星的任务
            for sat_id, sat_tasks in sat_groups.items():
                # 按开始时间排序
                sat_tasks.sort(key=lambda x: x['start_time'])

                merged_segments = {}
                current_group = []  # 当前连续任务组

                for task in sat_tasks:
                    if not current_group:
                        current_group.append(task)
                    else:
                        # 检查是否时间连续
                        last_task = current_group[-1]
                        if task['start_time'] == last_task['end_time']:
                            current_group.append(task)
                        else:
                            # 保存当前组
                            self._finalize_task_group(current_group, merged_segments)
                            current_group = [task]

                # 处理最后一组
                if current_group:
                    self._finalize_task_group(current_group, merged_segments)

                satellite_data[sat_id] = merged_segments

            merged_result[task_id] = satellite_data

        return merged_result

    def _finalize_task_group(self, task_group, merged_segments):
        """处理一个连续任务组的合并"""
        if not task_group:
            return

        # 获取组内最早任务
        first_task = task_group[0]
        # 获取组内最晚任务
        last_task = task_group[-1]

        # 计算总消耗（根据首尾状态）
        battery_cost = first_task['battery_before_task'] - last_task['battery_after_task']
        storage_added = last_task['current_storage'] - first_task.get('storage_before_task', 0)

        # 计算累计观测/机动时间
        total_obs = sum(t.get('observation_time', 0) for t in task_group)
        total_maneuver = sum(t.get('maneuver_duration', 0) for t in task_group)

        # 生成时间键
        time_key = f"{first_task['start_time'].strftime('%Y-%m-%d %H:%M:%S')}," \
                   f"{last_task['end_time'].strftime('%Y-%m-%d %H:%M:%S')}"
        # 转换为字符串（自定义格式）
        str_windows = []
        sat_windows = first_task['sat_windows']
        for start, end in sat_windows:
            # 格式说明：%Y=年，%m=月，%d=日，%H=时（24h），%M=分，%S=秒，%Z=时区
            start_str = start.strftime("%Y-%m-%d %H:%M:%S")
            end_str = end.strftime("%Y-%m-%d %H:%M:%S")
            str_windows.append((start_str, end_str))
        if first_task['sensor_type'] == 'optical':
            light_flag = "有"
        else:
            light_flag = "未检查"
        merged_segments[time_key] = {
            'cluster_name': last_task['cluster_name'],
            'battery_cost': max(battery_cost, 0),  # 确保不为负
            'storage_added': max(storage_added, 0),
            'battery_before': first_task['battery_before_task'],
            'battery_after': last_task['battery_after_task'],
            'storage_before': first_task.get('storage_before_task', 0),
            'storage_after': last_task['current_storage'],
            'sensor_type': first_task['sensor_type'],
            'task_type': first_task['task_type'],
            'priority': first_task.get('priority'),
            'boundary_points': first_task.get('parent_area'),
            'target_location': first_task.get('target_location'),
            'observation_time': total_obs,
            'maneuver_time': total_maneuver,
            'battery_cap': first_task['battery_cap'],
            'storage_cap': first_task['storage_cap'],
            'subtask_count': len(task_group),  # 新增：记录包含多少个子任务,
            'cloud_extent': first_task['cloud_extent'],
            'light_power': light_flag,
            'sat_windows': str_windows,
            'task_name': first_task['task_name']
        }

    def _translate_sensor_type(self, sensor_type):
        """转换传感器类型为中文"""
        mapping = {
            'optical': '可见光',
            'infrared': '红外',
            'SAR': '合成孔径雷达'
        }
        return mapping.get(sensor_type, sensor_type)

    def save_to_excel(self, schedule, filename, txtfilename):
        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import PatternFill, Font, Alignment
            import os
        except ImportError:
            print("保存Excel需要pandas和openpyxl库。请安装：pip install pandas openpyxl")
            return False
        """保存合并后的调度结果，支持区域目标的边界点显示"""
        merged = self.merge_subtasks(schedule)

        text_content = []
        excel_rows = []

        for task_id, satellites in merged.items():
            for sat_id, time_windows in satellites.items():
                for time_range, data in time_windows.items():
                    start_str, end_str = time_range.split(',')
                    start_dt = pd.to_datetime(start_str)
                    end_dt = pd.to_datetime(end_str)
                    duration_min = (end_dt - start_dt).total_seconds() / 60

                    # 获取任务类型（假设数据中有task_type字段）
                    task_type = data.get('task_type', '未知类型')

                    # ========== 构建文本内容 ==========
                    text_lines = [
                        f"▷ 任务名称:{data['task_name']},任务id: {task_id} (优先级: {data.get('priority', '无')})",
                        f"星簇：{data['cluster_name']}中卫星: {sat_id}于{start_str}执行{task_type}任务\n"
                        f"卫星: {sat_id}对于该任务目标的可见时间窗范围为：{data['sat_windows']}"
                    ]

                    # print("在报存excel时候的任务类型:", task_id, task_type)
                    # 区域目标特殊处理
                    if (task_type == "区域目标" or task_type == "广域目标") and data.get('boundary_points'):
                        text_lines.append(
                            f"使用{self._translate_sensor_type(data['sensor_type'])}类型载荷对目标区域进行观测")
                        text_lines.append("目标区域边界坐标点(纬度,经度)：")
                        # 添加所有边界点（每行显示2个点）
                        points = data['boundary_points']
                        print(f"save中边界点为{points}")
                        for i in range(0, len(points), 2):
                            line = []
                            for lat, lon in points[i:i + 2]:
                                line.append(f"({lat:.2f}°, {lon:.2f}°)")
                            text_lines.append("  ".join(line))
                    else:
                        # 常规点目标处理
                        lat, lon = data.get('target_location', (0, 0))
                        text_lines.append(f"使用{self._translate_sensor_type(data['sensor_type'])}类型载荷对目标位置:")
                        text_lines.append(f"(纬度: {lat:.2f}°, 经度: {lon:.2f}°)进行观测")

                    # 添加通用信息
                    text_lines.extend([
                        f"目标区域云层厚度为: {data['cloud_extent']:.2f}米, 光照情况: {data['light_power']}",
                        f"机动时间: {data['maneuver_time']:.2f}秒, 观测时间: {data['observation_time']:.2f}秒",
                        f"任务于{end_str}执行完毕, 共计耗时: {duration_min:.2f}分钟",
                        f"任务执行消耗电量: {data['battery_cost']:.2f}Wh, 剩余电量: {data['battery_after']:.2f}Wh",
                        f"星上增加存储容量: {data['storage_added']:.2f}GB, 剩余容量: {data['storage_cap'] - data['storage_after']:.2f}GB",
                        "-" * 50
                    ])

                    text_content.append("\n".join(text_lines))

                    # ========== Excel数据准备 ==========
                    excel_row = {
                        '任务ID': task_id,
                        '任务名称': data['task_name'],
                        '任务类型': task_type,
                        '星簇名': data['cluster_name'],
                        '卫星ID': sat_id,
                        '开始时间': start_str,
                        '结束时间': end_str,
                        '持续时间(分)': f"{duration_min:.2f}",
                        '光照情况(有/无)': data['light_power'],
                        '云层厚度': data['cloud_extent'],
                        '传感器类型': self._translate_sensor_type(data['sensor_type']),
                        '电量消耗(Wh)': f"{data['battery_cost']:.2f}",
                        '剩余电量(Wh)': f"{data['battery_after']:.2f}",
                        '存储增加(GB)': f"{data['storage_added']:.2f}",
                        '剩余存储(GB)': f"{data['storage_cap'] - data['storage_after']:.2f}",
                        "卫星对任务可见时间窗": data['sat_windows']
                    }

                    # 区域目标添加边界点（Excel中合并为一个单元格）
                    if task_type == '区域目标' and data.get('boundary_points'):
                        excel_row['目标信息'] = "目标区域\n边界点:" + "\n".join(
                            f"({lat:.6f},{lon:.6f})" for lat, lon in data['boundary_points']
                        )
                    else:
                        lat, lon = data.get('target_location', (0, 0))
                        excel_row['目标信息'] = f"点目标\n({lat:.6f}, {lon:.6f})"

                    excel_rows.append(excel_row)

        # 保存文本报告
        with open(txtfilename, 'w', encoding='utf-8') as f:
            f.write("========== 卫星任务调度报告 ==========\n\n")
            f.write("\n\n".join(text_content))

        # 保存Excel（优化列宽）
        if excel_rows:
            df = pd.DataFrame(excel_rows)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)

                # 调整列宽
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']
                for col in worksheet.columns:
                    max_length = max(len(str(cell.value)) for cell in col)
                    worksheet.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

        print(f"报告已保存: {txtfilename} | {filename}")
        return True

    def save_to_excel1(self, schedule, filename, txtfilename):
        """将调度结果保存到Excel文件，包括已分配和未分配的任务"""
        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
            from openpyxl.utils.dataframe import dataframe_to_rows
            import os
        except ImportError:
            print("保存Excel需要pandas和openpyxl库。请安装：pip install pandas openpyxl")
            return False

        if not schedule and not hasattr(self, 'tasks'):
            print("调度为空且没有任务信息，未保存Excel文件")
            return False

        # 创建工作簿
        wb = Workbook()
        # 处理已分配的任务
        if schedule:
            # 预处理数据
            data = []
            for item in schedule:
                # 格式化开始和结束时间
                start_time_str = item['start_time'].strftime('%Y-%m-%d %H:%M:%S')
                end_time_str = item['end_time'].strftime('%Y-%m-%d %H:%M:%S')

                # 计算持续时间（分钟）
                duration_minutes = (item['end_time'] - item['start_time']).total_seconds() / 60

                observation_value = item.get('observation_time')
                observation_seconds = observation_value.total_seconds() if isinstance(observation_value,
                                                                                      timedelta) else (
                    observation_value if isinstance(observation_value, (int, float)) else 0)
                maneuver_value = item.get('maneuver_duration')
                maneuver_seconds = maneuver_value.total_seconds() if isinstance(maneuver_value, timedelta) else (
                    maneuver_value if isinstance(maneuver_value, (int, float)) else 0)

                # 获取任务目标位置
                lat, lon = item['target_location']
                # 处理姿态四元数，转换为欧拉角
                attitude_after = np.array(item.get('attitude_after_task'))
                roll, pitch, yaw = None, None, None
                if attitude_after is not None and isinstance(attitude_after, np.ndarray) and len(attitude_after) == 4:
                    try:
                        roll, pitch, yaw = quaternion_to_euler(attitude_after)
                    except Exception as e:
                        print(f"Error converting quaternion to Euler for task {item['task_id']}: {e}")
                        # 如果转换失败，设置为None
                        roll, pitch, yaw = None, None, None
                # 添加到数据列表
                intersection = set(item['cluster_name']).intersection(set(item['sat_cluster_name']))
                result = ', '.join(intersection)
                # print(f"观测时间{observation_seconds}")
                sensor_type = item['sensor_type']
                if sensor_type == 'optical':
                    sensor_type = '可见光'
                if sensor_type == 'infrared':
                    sensor_type = '红外'
                if sensor_type == 'SAR':
                    sensor_type = '合成孔径雷达'
                data.append({
                    '星簇id': result,
                    '卫星ID': item['satellite_id'],
                    '任务ID': item['task_id'],
                    '任务类型': item['task_type'],
                    '载荷类型': sensor_type,
                    '优先级': item['priority'],
                    '开始时间': start_time_str,
                    '开始时间_原始': item['start_time'],  # 用于排序，后面会删除
                    '结束时间': end_time_str,
                    '持续时间(分钟)': round(duration_minutes, 2),
                    '成像时间(秒)': round(observation_seconds, 2),
                    '机动时间(秒)': round(maneuver_seconds, 2),
                    '任务前电量(%)': round(item.get('battery_before_task', 0) / self._get_satellite_by_id(
                        item['satellite_id']).battery_capacity * 100, 2),
                    '任务后电量(%)': round(item.get('battery_after_task', 0) / self._get_satellite_by_id(
                        item['satellite_id']).battery_capacity * 100, 2),
                    '存储使用(GB)': str(round(item.get('storage_after_task', 0), 2)),  # 新增round()
                    '目标纬度': round(lat, 6),
                    '目标经度': round(lon, 6),
                    '姿态侧摆角 (deg)': f"{round(roll, 2):.2f}" if roll is not None else "",  # 统一格式
                    '姿态俯仰角 (deg)': f"{round(pitch, 2):.2f}" if pitch is not None else "",
                    '星上存储任务': ', '.join(map(str, item.get('stored_tasks_after_task', [])))
                })
            # 按星簇和卫星分组
            from collections import defaultdict
            cluster_satellites = defaultdict(lambda: defaultdict(list))

            for item in sorted(data, key=lambda x: x['开始时间_原始']):
                cluster_satellites[item['星簇id']][item['卫星ID']].append(item)

            # 写入文件
            with open(txtfilename, 'w', encoding='utf-8') as f:
                for cluster, satellites in cluster_satellites.items():
                    f.write(f"\n\n========== 星簇: {cluster} ==========\n")

                    for sat_id, tasks in satellites.items():
                        f.write(f"\n◆ 卫星: {sat_id}\n")
                        f.write("-" * 50 + "\n")

                        for task in tasks:
                            f.write(f"▷ 任务: {task['任务ID']} (优先级: {task['优先级']})\n")
                            f.write(f"卫星:{sat_id}于{task['开始时间']}执行{task['任务类型']}任务：{task['任务ID']}\n"
                                    f"使用{task['载荷类型']}类型载荷对目标位置(纬度：{round(task['目标纬度'], 2)}°, 经度：{round(task['目标经度'], 2)}°)进行观测\n"
                                    f"机动时间：{task['机动时间(秒)']}秒,成像持续：{task['成像时间(秒)']}秒\n"
                                    f"任务于{task['结束时间']}执行完毕,共计耗时:{task['持续时间(分钟)']} 分钟\n"
                                    f"任务执行消耗电量: {float(task['任务前电量(%)']) - float(task['任务后电量(%)']):.2f}%,剩余电量：{task['任务后电量(%)']}%\n"
                                    f"任务后星上存储总使用量{task['存储使用(GB)']}GB,星上存储任务: {task['星上存储任务']}\n")
                            # f.write(f"  时间: {task['开始时间']} → {task['结束时间']} "
                            #         f"(持续: {task['持续时间(分钟)']} 分钟 = 观测{task['观测时间(秒)']}s + 机动{task['机动时间(秒)']}s)\n")
                            # f.write(f"  目标位置: ({task['目标纬度']}, {task['目标经度']})\n")
                            # f.write(
                            #     f"  姿态: Roll={task['姿态 Roll (deg)']}° | Pitch={task['姿态 Pitch (deg)']}° | Yaw={task['姿态 Yaw (deg)']}°\n")
                            # f.write(f"  电量: {task['任务前电量(%)']}% → {task['任务后电量(%)']}% "
                            #         f"(消耗: {float(task['任务前电量(%)']) - float(task['任务后电量(%)']):.2f}%)\n")
                            # f.write(f"  存储: 使用 {task['存储使用(GB)']}GB | 存储任务: {task['星上存储任务']}\n")
                            f.write("-" * 50 + "\n")
            print(f"操作日志已保存至 {os.path.abspath(txtfilename)}")
            # 创建DataFrame
            df = pd.DataFrame(data)

            # 按卫星ID和开始时间排序
            df = df.sort_values(by=['卫星ID', '开始时间_原始'])

            # 删除用于排序的原始时间列
            df = df.drop(columns=['开始时间_原始'])

            # 第一个工作表：按卫星和时间排序
            ws = wb.active
            ws.title = "卫星任务调度(按卫星和时间排序)"

            # 添加数据
            for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
                for c_idx, value in enumerate(row, 1):
                    ws.cell(row=r_idx, column=c_idx, value=value)

            # 设置列宽
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                ws.column_dimensions[column_letter].width = max_length + 2

            # 设置样式
            header_fill = PatternFill(start_color="B8CCE4", end_color="B8CCE4", fill_type="solid")
            header_font = Font(bold=True)

            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # 为各卫星的任务应用不同颜色
            satellites_used = sorted(set(item['卫星ID'] for item in data))
            satellite_colors = {
                sat_id: f"{(i * 40 + 200) % 256:02X}{(i * 70 + 100) % 256:02X}{(i * 50 + 150) % 256:02X}"
                for i, sat_id in enumerate(satellites_used)
            }

            # 从第二行开始应用颜色和分组
            current_sat = None
            for row in range(2, len(data) + 2):
                sat_id = ws.cell(row=row, column=2).value  # 卫星ID在第二列

                # 如果卫星ID改变，添加分隔线
                if current_sat is not None and sat_id != current_sat:
                    # 为上一个卫星的最后一行添加底部边框
                    for col in range(1, len(df.columns) + 1):
                        ws.cell(row=row - 1, column=col).border = Border(bottom=Side(style='medium'))

                current_sat = sat_id

                # 应用颜色
                if sat_id in satellite_colors:
                    fill = PatternFill(start_color=satellite_colors[sat_id],
                                       end_color=satellite_colors[sat_id],
                                       fill_type="solid")
                    for col in range(1, len(df.columns) + 1):
                        cell = ws.cell(row=row, column=col)
                        cell.fill = fill

            # 为最后一个卫星的最后一行添加底部边框
            if len(data) > 0:
                for col in range(1, len(df.columns) + 1):
                    ws.cell(row=len(data) + 1, column=col).border = Border(bottom=Side(style='medium'))

            # 第二个工作表：按时间排序
            ws2 = wb.create_sheet(title="按时间排序")

            # 按时间排序
            df_time = pd.DataFrame(data)
            df_time['开始时间_原始'] = [item['start_time'] for item in schedule]
            df_time = df_time.sort_values(by=['开始时间_原始'])
            df_time = df_time.drop(columns=['开始时间_原始'])

            # 添加表头
            headers = list(df_time.columns)
            for col, header in enumerate(headers, 1):
                cell = ws2.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # 添加数据
            for r_idx, row in enumerate(dataframe_to_rows(df_time, index=False, header=False), 2):
                for c_idx, value in enumerate(row, 1):
                    ws2.cell(row=r_idx, column=c_idx, value=value)

                    # 应用卫星对应的颜色
                    if len(df_time) > 0:
                        sat_id = df_time.iloc[r_idx - 2]['卫星ID']
                        if sat_id in satellite_colors:
                            fill = PatternFill(start_color=satellite_colors[sat_id],
                                               end_color=satellite_colors[sat_id],
                                               fill_type="solid")
                            ws2.cell(row=r_idx, column=c_idx).fill = fill

            # 设置第二个工作表的列宽
            for column in ws2.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                ws2.column_dimensions[column_letter].width = max_length + 2

            # 第三个工作表：甘特图数据
            ws3 = wb.create_sheet(title="甘特图数据")

            # 添加甘特图所需数据，按卫星和时间排序
            gantt_headers = ['卫星ID', '任务ID', '开始时间', '结束时间', '优先级']
            for col, header in enumerate(gantt_headers, 1):
                cell = ws3.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font

            # 获取甘特图数据，按卫星和时间排序
            gantt_data = []
            for item in schedule:
                gantt_data.append({
                    '卫星ID': item['satellite_id'],
                    '任务ID': item['task_id'],
                    '开始时间': item['start_time'],
                    '开始时间_str': item['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    '结束时间': item['end_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    '优先级': item['priority']
                })

            # 排序并写入
            if gantt_data:
                gantt_df = pd.DataFrame(gantt_data)
                gantt_df = gantt_df.sort_values(by=['卫星ID', '开始时间'])

                for row, item in enumerate(gantt_df.to_dict('records'), 2):
                    ws3.cell(row=row, column=1, value=item['卫星ID'])
                    ws3.cell(row=row, column=2, value=item['任务ID'])
                    ws3.cell(row=row, column=3, value=item['开始时间_str'])
                    ws3.cell(row=row, column=4, value=item['结束时间'])
                    ws3.cell(row=row, column=5, value=item['优先级'])

                    # 应用颜色
                    sat_id = item['卫星ID']
                    if sat_id in satellite_colors:
                        fill = PatternFill(start_color=satellite_colors[sat_id],
                                           end_color=satellite_colors[sat_id],
                                           fill_type="solid")
                        for col in range(1, 6):
                            ws3.cell(row=row, column=col).fill = fill

            # 设置第三个工作表的列宽
            for column in ws3.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                ws3.column_dimensions[column_letter].width = max_length + 2

        # 添加第四个工作表：未分配的任务
        ws4 = wb.create_sheet(title="未分配的任务")

        # 获取所有已分配任务的ID
        assigned_task_ids = set()
        if schedule:
            assigned_task_ids = {item['task_id'] for item in schedule}

        # 获取未分配的任务
        unassigned_tasks = []
        if hasattr(self, 'tasks'):
            for task in self.tasks:
                if task.task_id not in assigned_task_ids:
                    # 获取任务的基本信息
                    lat, lon = task.target_location

                    # 格式化时间窗口
                    earliest_start = task.earliest_start_time.strftime(
                        '%Y-%m-%d %H:%M:%S') if task.earliest_start_time else "未指定"
                    latest_end = task.latest_end_time.strftime('%Y-%m-%d %H:%M:%S') if task.latest_end_time else "未指定"

                    # 添加到未分配列表
                    unassigned_tasks.append({
                        '任务ID': task.task_id,
                        '优先级': task.priority,
                        '传感器类型': task.sensor_type,
                        '最早开始时间': earliest_start,
                        '最晚结束时间': latest_end,
                        '目标纬度': round(lat, 6),
                        '目标经度': round(lon, 6),
                        '目标长度(米)': task.target_length,
                        '目标宽度(米)': task.target_width,
                        '分辨率(米)': task.resolution
                    })

        # 如果有未分配的任务，添加到工作表
        if unassigned_tasks:
            # 按优先级排序
            unassigned_df = pd.DataFrame(unassigned_tasks)
            unassigned_df = unassigned_df.sort_values(by=['优先级'], ascending=False)

            # 添加表头
            headers = list(unassigned_df.columns)
            for col, header in enumerate(headers, 1):
                cell = ws4.cell(row=1, column=col, value=header)
                cell.fill = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid")
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # 添加数据
            for r_idx, row in enumerate(dataframe_to_rows(unassigned_df, index=False, header=False), 2):
                for c_idx, value in enumerate(row, 1):
                    ws4.cell(row=r_idx, column=c_idx, value=value)

                    # 根据优先级着色
                    priority = unassigned_df.iloc[r_idx - 2]['优先级']
                    # 高优先级任务用红色突出显示
                    if priority >= 4:
                        fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
                        ws4.cell(row=r_idx, column=c_idx).fill = fill

            # 设置列宽
            for column in ws4.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                ws4.column_dimensions[column_letter].width = max_length + 2
        else:
            # 如果没有未分配的任务，显示一条消息
            ws4.cell(row=1, column=1, value="所有任务都已成功分配")
            ws4.cell(row=1, column=1).font = Font(bold=True)

        # 添加总结工作表
        ws5 = wb.create_sheet(title="调度摘要")

        # 计算调度统计数据
        total_tasks = len(self.tasks) if hasattr(self, 'tasks') else 0
        assigned_tasks = len(schedule) if schedule else 0
        unassigned_tasks_count = total_tasks - assigned_tasks
        assignment_rate = assigned_tasks / total_tasks * 100 if total_tasks > 0 else 0

        # 按优先级统计
        priority_counts = {}
        priority_assigned = {}
        if hasattr(self, 'tasks'):
            for task in self.tasks:
                priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1
                priority_assigned[task.priority] = 0

        if schedule:
            for item in schedule:
                priority = item['priority']
                priority_assigned[priority] = priority_assigned.get(priority, 0) + 1

        # 按卫星统计
        satellite_counts = {}
        if schedule:
            for item in schedule:
                sat_id = item['satellite_id']
                satellite_counts[sat_id] = satellite_counts.get(sat_id, 0) + 1

        # 写入总结数据
        row = 1
        ws5.cell(row=row, column=1, value="调度摘要")
        ws5.cell(row=row, column=1).font = Font(bold=True, size=14)
        row += 2

        ws5.cell(row=row, column=1, value="总任务数:")
        ws5.cell(row=row, column=2, value=total_tasks)
        row += 1

        ws5.cell(row=row, column=1, value="已分配任务数:")
        ws5.cell(row=row, column=2, value=assigned_tasks)
        row += 1

        ws5.cell(row=row, column=1, value="未分配任务数:")
        ws5.cell(row=row, column=2, value=unassigned_tasks_count)
        row += 1

        ws5.cell(row=row, column=1, value="任务分配率:")
        ws5.cell(row=row, column=2, value=f"{assignment_rate:.2f}%")
        row += 2

        # 按优先级显示统计
        ws5.cell(row=row, column=1, value="按优先级统计")
        ws5.cell(row=row, column=1).font = Font(bold=True)
        row += 1

        ws5.cell(row=row, column=1, value="优先级")
        ws5.cell(row=row, column=2, value="总数")
        ws5.cell(row=row, column=3, value="已分配")
        ws5.cell(row=row, column=4, value="分配率")
        for cell in ws5[row]:
            if cell.value:
                cell.font = Font(bold=True)
        row += 1

        for priority in sorted(priority_counts.keys(), reverse=True):
            total = priority_counts[priority]
            assigned = priority_assigned.get(priority, 0)
            rate = assigned / total * 100 if total > 0 else 0

            ws5.cell(row=row, column=1, value=priority)
            ws5.cell(row=row, column=2, value=total)
            ws5.cell(row=row, column=3, value=assigned)
            ws5.cell(row=row, column=4, value=f"{rate:.2f}%")

            # 高优先级的未完全分配用红色突出显示
            if priority >= 4 and rate < 100:
                for col in range(1, 5):
                    ws5.cell(row=row, column=col).fill = PatternFill(
                        start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")

            row += 1

        row += 2

        # 按卫星显示统计
        if satellite_counts:
            ws5.cell(row=row, column=1, value="按卫星统计")
            ws5.cell(row=row, column=1).font = Font(bold=True)
            row += 1

            ws5.cell(row=row, column=1, value="卫星ID")
            ws5.cell(row=row, column=2, value="分配任务数")
            for cell in ws5[row]:
                if cell.value:
                    cell.font = Font(bold=True)
            row += 1

            for sat_id in sorted(satellite_counts.keys()):
                ws5.cell(row=row, column=1, value=sat_id)
                ws5.cell(row=row, column=2, value=satellite_counts[sat_id])

                # 应用卫星对应的颜色
                if sat_id in satellite_colors:
                    fill = PatternFill(start_color=satellite_colors[sat_id],
                                       end_color=satellite_colors[sat_id],
                                       fill_type="solid")
                    ws5.cell(row=row, column=1).fill = fill
                    ws5.cell(row=row, column=2).fill = fill

                row += 1

        # 设置摘要工作表的列宽
        for column in ws5.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            ws5.column_dimensions[column_letter].width = max_length + 5

        # 保存文件
        try:
            wb.save(filename)
            print(f"调度结果已保存到 {os.path.abspath(filename)}")
            return True
        except Exception as e:
            print(f"保存Excel文件时出错: {e}")
            return False

    def _get_satellite_by_id(self, sat_id):
        """根据卫星ID查找卫星对象"""
        for satellite in self.satellites:
            if satellite.sat_id == sat_id:
                return satellite
        return None

    def _preprocess(self):
        for task in self.tasks:
            for satellite in self.satellites:
                # 检查 cluster_names（如果 task.cluster_names 为 None 则跳过检查）
                if task.cluster_names is not None and task.cluster_names != [None]:
                    common_clusters = set(task.cluster_names) & set(satellite.cluster_names)
                    if not common_clusters:
                        # print(f"[跳过] 卫星 {satellite.sat_id} 与任务 {task.task_id} 没有共同星簇")
                        # print(f"  task.cluster_names = {task.cluster_names}")
                        # print(f"  satellite.cluster_names = {satellite.cluster_names}")
                        continue

                # 检查 sensor_type（如果 task.sensor_type 为 None 则跳过检查）
                conditions = True
                if hasattr(task, 'sensor_type') and task.sensor_type is not None:
                    if satellite.sensor_type != task.sensor_type:
                        # print(f"[跳过] 卫星 {satellite.sat_id} 的传感器类型不匹配任务 {task.task_id}")
                        # print(f"  task.sensor_type = {task.sensor_type}")
                        # print(f"  satellite.sensor_type = {satellite.sensor_type}")
                        conditions = False

                # 检查 resolution（如果 task.resolution 为 None 则跳过检查）
                if hasattr(task, 'resolution') and task.resolution is not None:
                    if satellite.resolution_capability > task.resolution:
                        # print(f"[跳过] 卫星 {satellite.sat_id} 的分辨率不满足任务 {task.task_id}")
                        # print(f"  task.resolution = {task.resolution}")
                        # print(f"  satellite.resolution_capability = {satellite.resolution_capability}")
                        conditions = False

                if not conditions:
                    continue

                # 检查可见时间窗口
                if not hasattr(task, 'visible_windows') or not isinstance(task.visible_windows, dict):
                    # print(f"[跳过] 任务 {task.task_id} 没有可见时间窗口信息或格式错误")
                    continue

                if satellite.sat_id not in task.visible_windows:
                    # print(f"[跳过] 卫星 {satellite.sat_id} 不在任务 {task.task_id} 的可见时间窗口中")
                    continue

                # 处理每个时间窗口
                for tw_start, tw_end in task.visible_windows[satellite.sat_id]:
                    valid_start = max(tw_start, task.earliest_start_time, self.start_time)
                    valid_end = min(tw_end, task.latest_end_time, self.end_time)
                    if valid_end > valid_start:
                        task.add_available_satellite(satellite, valid_start, valid_end)
                    else:
                        pass
                        # print(f"[跳过] 卫星 {satellite.sat_id} 在任务 {task.task_id} 中没有有效时间窗口")
                        # print(f"  tw_start = {tw_start}, tw_end = {tw_end}")
                        # print(
                        #     f"  earliest_start_time = {task.earliest_start_time}, latest_end_time = {task.latest_end_time}")
                        # print(f"  self.start_time = {self.start_time}, self.end_time = {self.end_time}")


def euler_to_quaternion(roll, pitch, yaw):
    """欧拉角转四元数，返回numpy.ndarray类型"""
    roll = np.radians(roll)
    pitch = np.radians(pitch)
    yaw = np.radians(yaw)

    cr = np.cos(roll * 0.5)
    sr = np.sin(roll * 0.5)
    cp = np.cos(pitch * 0.5)
    sp = np.sin(pitch * 0.5)
    cy = np.cos(yaw * 0.5)
    sy = np.sin(yaw * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return np.array([w, x, y, z])


def calculate_boundary_quaternions(roll_limit=(-45, 45), pitch_limit=(-45, 45), yaw_limit=(-45, 45)):
    """计算角度边界值对应的四元数"""
    boundary_quaternions = []
    # 遍历滚转角的边界值
    for roll in roll_limit:
        # 遍历俯仰角的边界值
        for pitch in pitch_limit:
            # 遍历偏航角的边界值
            for yaw in yaw_limit:
                quaternion = euler_to_quaternion(roll, pitch, yaw)
                boundary_quaternions.append(quaternion)
    return boundary_quaternions
