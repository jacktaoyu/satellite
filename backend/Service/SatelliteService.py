import math
import os
import pickle
import random
import time
import numpy as np
from openpyxl.reader.excel import load_workbook
from skyfield.api import wgs84, load
from datetime import datetime, timedelta, timezone
from pyproj import Transformer
from random import choice
from config import sunlight_powers, INTER_VAL_TIME, GROUND_RATE, GROUND_STATION


# 单个卫星
class Satellite:
    def __init__(self, **kwargs):
        """
        创建一个卫星代理
        :param kwargs:不定个数的参数字典
        """
        # 卫星属性
        self.sat_id = kwargs.get('sat_id')
        self.sat_name = kwargs.get('sat_name')
        self.tle_line1 = kwargs.get('tle_line1')
        self.tle_line2 = kwargs.get('tle_line2')
        self.orbit = kwargs.get('orbit')  # 卫星所处轨道
        self.alias = f"第{self.orbit}轨道第{self.sat_name.split('_')[2]}卫星"
        self.sat_model = kwargs.get('sat_model')  # 卫星的轨道
        self.max_storage = kwargs.get('storage', 500)  # 最大存储容量,单位：M,默认500GB
        self.storage = 0  # 存储
        self.battery_capacity = kwargs.get('battery', 5000)  # Wh 电池容量，默认5000Wh
        self.battery = self.battery_capacity  # Wh 电池电量

        self.downlink_rate = kwargs.get('downlink_rate', 4)  # 下行数据速率,单位：GB/s
        self.eclipse_powers = kwargs.get('eclipse_powers', 8)  # 单位：W  遮挡功率
        self.sunlight_powers = kwargs.get('sunlight_powers', 300)  # 单位：W  太阳能功率
        self.maneuver_powers = kwargs.get('maneuver_powers', 500)  # 单位：W  机动功率
        self.imaging_powers = kwargs.get('imaging_powers', 700)  # 单位：W  成像功率
        # 所属星簇
        self.belong_cluster = []  # 所属星簇name的列表

        # 载荷属性
        self.star_payload = kwargs.get('sensor_type')  # 卫星搭载的载荷类型
        self.resolution_capability = kwargs.get('resolution_capability', 1.0)  # 单位：m  分辨率
        self.width_of_cloth = kwargs.get('width_of_cloth', 50)  # 单位：km 幅宽
        # 幅宽范围检查
        if self.width_of_cloth < 12 or self.width_of_cloth > 50:
            self.width_of_cloth = random.randint(12, 50)
        self.angle_velocity = kwargs.get('angle_velocity', 1.0)  # 单位：弧度 载荷的角度转动速度，默认1°,1/180pi
        self.stable_time = kwargs.get('stable_time', 10)  # 稳定时间,默认10秒
        self.side_swing_angle = 0.0  # 单位：弧度。初始侧摆角度
        self.pitch_angle = 0.0  # 单位：弧度。初始俯仰角度
        self.side_swing_angle_Max = kwargs.get('max_roll_angle', 45)  # 单位：弧度。最大侧摆角度
        self.pitch_angle_Max = kwargs.get('max_pitch_angle', 45)  # 单位：弧度。最大俯仰角度

        # 计算轨道高度
        self.orbital_altitude = self.calculate_orbital_altitude()
        h = self.orbital_altitude
        theta_max = self.side_swing_angle_Max
        # 若为角度，转为弧度
        if theta_max > np.pi:  # 角度
            theta_max = np.radians(theta_max)
        # 使用平面近似计算最大地面覆盖距离
        self.d_max = h * np.tan(theta_max)
        print("轨道高度", self.orbital_altitude, "覆盖范围", self.d_max)

        self.working_mode = None  # 工作模式
        self.position = None  # 卫星位置
        self.speed = None  # 卫星速度
        self.sub_point = None  # 卫星星下点

        mean_motion = self.sat_model.model.no  # 直接访问底层 SGP4 模型的属性,获取平均运动 n (单位: 圈/天)
        # print(mean_motion)
        # 计算轨道周期 (秒)
        self.orbital_period_seconds = 2 * math.pi * 60 / mean_motion
        # print(self.orbital_period_seconds)
        self.orbit_number = 0  # 轨道圈数，初始为0

        self.status = "FREE"  # 载荷状态: FREE, BUSY
        self.is_available = True  # 是否可用
        self.running_task = None  # 正在执行的任务
        self.connecting_ground_station = None  # 连接的地面站
        self.connecting_geo = None  # 当前连接的高轨卫星名称
        self.tasks_len = 0  # 任务列表长度
        self.client = kwargs.get('client')

        # 用于计算卫星轨迹和时间窗口的时间范围,7天的时间范围
        self.time_for_calculating_timeWindow = 86400  # 单位：秒
        self.interval_time = 300  # 单位：秒，时间间隔
        self.length_of_timeWindow = self.time_for_calculating_timeWindow / self.interval_time
        self.waiting_tasks_list = []  # 获取到时间窗口，等待执行的任务列表
        self.new_tasks_list = []  # 新到的任务列表(基于任务对象的priority属性进行排序)
        self.result_list = []  # 结果列表
        self.sat_trace = []  # 卫星轨迹

        # 资源信息
        # self.imaging_speed = 600000  # 成像速度（像素/秒）

        # 初始状态
        self.battery_level = self.battery
        self.current_storage = self.storage
        self.current_attitude = np.array([1, 0, 0, 0])  # 单位四元数，表示卫星初始姿态

        self.simulation_start_time = kwargs.get('simulation_start_time')  # 仿真开始时间
        self.end_time = kwargs.get('end_time')
        # 任务和时间窗口
        self.downlink_windows = []  # 数据下行时间窗口
        self.charging_windows = []  # 充电时间窗口（日照期）
        # self.downlink_windows = [[self.simulation_start_time, self.end_time]]  # 数据下行时间窗口
        # self.charging_windows = [[self.simulation_start_time, self.end_time]]  # 充电时间窗口（日照期）

        self.charge_window = None  # 充电时间窗口(动态)
        self.down_window = None  # 数传时间窗口(动态)

        # self.last_update_time = None  # 上次状态更新时间

        self.cloud_threshold = kwargs.get('cloud_threshold')
        # {
        #     'optical': 0.2,  # 可见光，要求较低的云雾 (例如 20% 阈值)
        #     'SAR': 1.1,  # SAR不受云雾影响，设置一个大于1的值，表示没有实际限制
        #     'infrared': 0.6  # 红外，比可见光要求低 (例如 60% 阈值)
        #     # 如果需要，可以根据 self.sensor_type 覆盖或添加更具体的阈值
        #     # 例如，如果主传感器是光学，可以默认将 satellite.cloud_threshold 设置为 0.2
        #     # 但为了灵活处理任务指定不同传感器的情况，使用字典更好
        # }

        # GEO卫星的位置（经度）
        self.geo_satellites = {
            '高轨卫星1': {'longitude': 120.0},  # 东经120度
            '高轨卫星2': {'longitude': 240.0},  # 东经240度
            '高轨卫星3': {'longitude': 0.0}  # 东经0度
        }
        self.geo_coverage_angle = 120  # GEO卫星的覆盖角度范围（度）

        print(self.client)

    def update_state(self, now_time, time_multiple, ground_stations):
        """
        更新卫星状态
        @:return 状态
        """
        # 更新卫星轨迹
        self.update_trace_window(time_multiple, now_time)
        # print("轨迹长度：", len(self.sat_trace), "条")
        # 更新卫星状态
        if self.sat_model:
            ts = load.timescale()
            t = ts.utc(now_time.replace(tzinfo=timezone.utc))
            geocentric = self.sat_model.at(t)
            self.position = geocentric.position.km
            self.speed = geocentric.velocity.km_per_s
            observatory = wgs84.subpoint(geocentric)
            self.sub_point = [round(observatory.latitude.degrees, 2), round(observatory.longitude.degrees, 2)]
            # 更新轨道圈数
            self.orbit_number = (now_time - self.simulation_start_time.replace(
                tzinfo=None)).total_seconds() // self.orbital_period_seconds
            # print("轨道圈数：", self.orbit_number)

            # 生成任务
            # time_diff = (now_time - self.simulation_start_time.replace(tzinfo=None)).total_seconds()
            # if time_diff <= 300 + 4 * INTER_VAL_TIME and "Cluster_10_infrared_0.5" in self.belong_cluster:
            # if "Cluster_10_infrared_0.5" in self.belong_cluster:
            #     # if "Cluster_10_infrared_1.0" in self.belong_cluster:
            #     subpoint = wgs84.subpoint(geocentric)
            #     lat = round(subpoint.latitude.degrees, 2)
            #     lon = round(subpoint.longitude.degrees, 2)
            #     type_of_payload = "移动目标"
            #     # if (lat - 22.54) <= 2 and (lon - 114.05) <= 2:
            #     #     type_of_payload = "海洋"
            #     # 加载工作簿和工作表
            #     wb = load_workbook("./library/example25.xlsx")
            #     sheet = wb.active
            #     # 获取最后一行的行号
            #     last_row = sheet.max_row
            #     # 写入下一行（如果工作表为空，last_row=0，下一行是 1）
            #     sheet.cell(row=last_row + 1, column=1, value=random.randint(1, 5))  # 优先级
            #     sheet.cell(row=last_row + 1, column=2, value="否")  # 优先级
            #     sheet.cell(row=last_row + 1, column=3, value=type_of_payload)  # 目标类型
            #     sheet.cell(row=last_row + 1, column=4, value=self.star_payload)  # 载荷类型
            #     sheet.cell(row=last_row + 1, column=5, value=self.resolution_capability)  # 分辨率
            #     sheet.cell(row=last_row + 1, column=6, value="(2025,6,6,6,0,00)-(2025,6,6,13,00,00)")  # 幅宽
            #     sheet.cell(row=last_row + 1, column=7, value=str([lat, lon]))  # 纬度，经度
            #     sheet.cell(row=last_row + 1, column=8, value="All_Sat")  # 星簇名
            #     sheet.cell(row=last_row + 1, column=11, value=500)  # 云层厚度
            #     sheet.cell(row=last_row + 1, column=12, value=self.sat_name)  # 卫星名称
            #
            #     # 保存工作簿
            #     wb.save("./library/example25.xlsx")

            # 检查是否在GEO卫星内
            self.check_geo_coverage(geocentric)

            # 更新电量,方案1
            # 添加调试信息
            if self.battery is None:
                print(f"警告: 卫星 {self.sat_name} 的电池电量为 None，重置为默认值")
                self.battery = self.battery_capacity

            if self.battery_capacity is None:
                print(f"警告: 卫星 {self.sat_name} 的电池容量为 None，设置为默认值 5000Wh")
                self.battery_capacity = 5000
                self.battery = self.battery_capacity

            if self.charge(t):
                # 充电功率等于光照功率减去自然消耗功率
                net_charge_rate = self.sunlight_powers - self.eclipse_powers
                self.battery += net_charge_rate * INTER_VAL_TIME / 3600
                # 如果电量超过最大容量，则设置为最大容量
                if self.battery > self.battery_capacity:
                    self.battery = self.battery_capacity
            else:
                if self.battery > 0:
                    self.battery -= self.eclipse_powers * INTER_VAL_TIME / 3600
                if self.battery <= 0:
                    self.battery = 0
                #  # 充电方案2
                # for charge_time in self.charging_windows:
                #     if charge_time[0] <= t < charge_time[1]:
                #         net_charge_rate = sunlight_powers['charge'] - sunlight_powers['idle']
                #         self.battery += net_charge_rate * INTER_VAL_TIME / 3600
                #         for i in self.charging_windows:
                #             if i[1] < t:
                #                 self.charging_windows.remove(i)
                #     else:
                #         if self.battery > 0:
                #             self.battery -= sunlight_powers['idle'] * INTER_VAL_TIME / 3600
                #         if self.battery <= 0:
                #             self.battery = 0
            # 数传
            t = t.utc_datetime()
            for dt in self.downlink_windows:
                if dt[0] <= t < dt[1]:  # 如果当前时间处于数传窗口内
                    nearest_station = choice(ground_stations)  # 随机选择一个地面站
                    # distance = ((nearest_station.location[0] - self.sub_point[0]) ** 2 + (
                    #         nearest_station.location[1] - self.sub_point[1]) ** 2)
                    # # 找出距离卫星最近的地面站
                    # for gs in ground_stations:
                    #     distance1 = ((gs.location[0] - self.sub_point[0]) ** 2 + (
                    #             gs.location[1] - self.sub_point[1]) ** 2)
                    #     if distance1 < distance:
                    #         nearest_station = gs

                    # 设置连接关系
                    # 如果之前有连接的地面站，从该地面站的连接集合中移除卫星
                    if self.connecting_ground_station and self.connecting_ground_station != nearest_station.name:
                        for gs in ground_stations:
                            if gs.name == self.connecting_ground_station:
                                gs.connecting_satellite.discard(self.sat_name)
                                break
                    # 更新连接关系
                    self.connecting_ground_station = nearest_station.name
                    nearest_station.connecting_satellite.add(self.sat_name)
                    # 更新存储
                    if self.storage < self.max_storage:
                        self.storage += self.downlink_rate * INTER_VAL_TIME
                        # 如果存储超过最大存储量，则设置为最大存储量
                        if self.storage > self.max_storage:
                            self.storage = self.max_storage
                    for i in self.downlink_windows:
                        if i[1] < t:
                            self.downlink_windows.remove(i)
                    break
                elif t < dt[0]:
                    if self.connecting_ground_station:
                        # 从之前连接的地面站中移除卫星
                        for gs in ground_stations:
                            if gs.name == self.connecting_ground_station:
                                gs.connecting_satellite.discard(self.sat_name)
                                break
                        self.connecting_ground_station = None
                    break

    def sat_trace_window(self, STRAT_TIME):
        """
        计算卫星在一定时间段内的轨道位置（轨迹）以及相关的地面观察点信息，并存储这些信息以便后续使用
        @return: 1
        @param STRAT_TIME: 仿真开始时间
        """
        # 如果卫星的轨迹数据sat_trace是空的，说明之前没有计算过轨迹，进入初始化阶段
        if not self.sat_trace:
            # # 计算轨迹
            # for i in range(0, self.time_for_calculating_timeWindow, self.interval_time):
            #     # 计算卫星在当前时间的地球中心坐标（geocentric）
            #     t = self.current_time_func(STRAT_TIME, i)
            #     # print(t.utc_datetime())
            #     geocentric = self.sat_model.at(t)
            #     # 将卫星的轨道位置投影到地球表面，得到卫星的地面投影点
            #     # subpoint = wgs84.subpoint(geocentric)
            #     # observatory = wgs84.latlon(subpoint.latitude.degrees,
            #     #                            subpoint.longitude.degrees)  # 将地球经纬度坐标转换为x_y_z三维坐标；ITRS(地固坐标系，随着地球转动)
            #     # 存储当前时间点的轨迹信息:卫星位置、地面子点和地面观察点,UTC时间。
            #     sat_trace_list = [geocentric, t]
            #     self.sat_trace.append(sat_trace_list)
            #
            #     # 计算卫星的数传窗口
            #     self.calculate_down_window(t, geocentric)

            # 保存轨迹数据
            # self.save_data(self.sat_trace, f"./static/trace/{self.sat_name}_trace.pkl")
            # self.save_data(self.downlink_windows, f"./static/downlink/{self.sat_name}_downlink.pkl")
            # self.sat_trace = None
            # self.downlink_windows = None

            # 读取轨迹数据
            self.sat_trace = self.load_data(f"./static/trace/{self.sat_name}_trace.pkl")
            self.downlink_windows = self.load_data(f"./static/downlink/{self.sat_name}_downlink.pkl")

            # if "Cluster_10_infrared_0.5" in self.belong_cluster:
            #     # if "Cluster_10_infrared_1.0" in self.belong_cluster:
            #     subpoint = wgs84.subpoint(geocentric)
            #     lat = round(subpoint.latitude.degrees + 0.5, 2)
            #     lon = round(subpoint.longitude.degrees + 0.5, 2)
            #     type_of_payload = "移动目标"
            #     # if (lat - 22.54) <= 2 and (lon - 114.05) <= 2:
            #     #     type_of_payload = "海洋"
            #     # 加载工作簿和工作表
            #     wb = load_workbook("./library/example25.xlsx")
            #     sheet = wb.active
            #     # 获取最后一行的行号
            #     last_row = sheet.max_row
            #     # 写入下一行（如果工作表为空，last_row=0，下一行是 1）
            #     sheet.cell(row=last_row + 1, column=1, value=random.randint(1, 5))  # 优先级
            #     sheet.cell(row=last_row + 1, column=2, value="否")  # 优先级
            #     sheet.cell(row=last_row + 1, column=3, value=type_of_payload)  # 目标类型
            #     sheet.cell(row=last_row + 1, column=4, value=self.star_payload)  # 载荷类型
            #     sheet.cell(row=last_row + 1, column=5, value=self.resolution_capability)  # 分辨率
            #     sheet.cell(row=last_row + 1, column=6, value="(2025,6,6,6,0,00)-(2025,6,6,13,00,00)")  # 幅宽
            #     sheet.cell(row=last_row + 1, column=7, value=str([lat, lon]))  # 纬度，经度
            #     sheet.cell(row=last_row + 1, column=8, value="All_Sat")  # 星簇名
            #     sheet.cell(row=last_row + 1, column=11, value=500)  # 云层厚度
            #     sheet.cell(row=last_row + 1, column=12, value=self.sat_name)  # 卫星名称
            #
            #     # 保存工作簿
            #     wb.save("./library/example25.xlsx")

            # 计算充电窗口
            # if self.charge(t):
            #     if self.charge_window is None:
            #         self.charge_window = [t.utc_datetime(), t.utc_datetime()]
            #     else:
            #         self.charge_window[1] = t.utc_datetime()
            # elif self.charge_window:
            #     self.charging_windows.append(self.charge_window)
            #     self.charge_window = None

        # print("充电窗口", self.charging_windows)
        # print("数传窗口", self.downlink_windows)

    def update_trace_window(self, time_multiple, now_time):
        """
        更新轨迹窗口
        """
        # 卫星在过去一段时间的位置信息，现在要滑动时间窗口，删掉最旧的数据，保留最新的
        for i in range(time_multiple):
            if self.sat_trace[0][1].utc_datetime() < now_time.replace(tzinfo=timezone.utc):
                # print("最旧的卫星轨迹数据点", self.sat_trace[0][1].utc_datetime(), "现在的系统时间", now_time)
                del self.sat_trace[0]
                # print("最新的卫星轨迹数据点", self.sat_trace[-1][1].utc_datetime())
            if len(self.sat_trace) < self.length_of_timeWindow:
                t = self.current_time_func(self.sat_trace[-1][1].utc_datetime(), self.interval_time)
                geocentric = self.sat_model.at(t)
                self.sat_trace.append([geocentric, t])

                # 更新数传窗口
                self.calculate_down_window(t, geocentric)

            # 更新充电窗口
            # if self.charge(t):
            #     if self.charge_window is None:
            #         self.charge_window = [t.utc_datetime(), t.utc_datetime()]
            #     else:
            #         self.charge_window[1] = t.utc_datetime()
            # elif self.charge_window:
            #     self.charging_windows.append(self.charge_window)
            #     self.charge_window = None

    def calculate_down_window(self, now_time, geocentric):
        """
        动态计算数传时间窗口
        :param now_time:    当前时间
        :param geocentric: 卫星当前时刻的地心坐标
        :return:
        """
        theta_roll_max = np.radians(self.side_swing_angle_Max)
        theta_pitch_max = np.radians(self.pitch_angle_Max)
        is_visible = False
        for lat, lon in GROUND_STATION.values():
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:4978")
            x_g, y_g, z_g = transformer.transform(lat, lon, 0)
            P_ground_ECEF = np.array([x_g, y_g, z_g])
            t = now_time  # 获取时间点
            P_sat_ECI = geocentric.position.km  # 卫星ECI坐标
            V_sat_ECI = geocentric.velocity.km_per_s  # 卫星速度矢量
            # 地球自转修正：ECEF → ECI
            P_ground_ECI = self.earth_rotation_matrix(t) @ P_ground_ECEF
            # 计算 LVLH 坐标系（Local Vertical, Local Horizontal）
            # Z轴指向地心
            Z_lvlh = -P_sat_ECI / np.linalg.norm(P_sat_ECI)
            # Y轴垂直于轨道平面
            Y_lvlh = np.cross(P_sat_ECI, V_sat_ECI)
            Y_lvlh = Y_lvlh / np.linalg.norm(Y_lvlh)
            # X轴完成右手坐标系
            X_lvlh = np.cross(Y_lvlh, Z_lvlh)

            # 构建旋转矩阵（ECI到LVLH的坐标变换）
            R_ECI_to_LVLH = np.vstack([X_lvlh, Y_lvlh, Z_lvlh])

            # 计算地面目标相对于卫星的矢量（ECI坐标系）
            vec_target_ECI = P_ground_ECI - P_sat_ECI

            # 将目标矢量转换到LVLH坐标系
            vec_target_LVLH = R_ECI_to_LVLH @ vec_target_ECI
            X, Y, Z = vec_target_LVLH

            # 计算侧视角与俯仰角
            theta_roll = np.arctan2(Y, Z)
            theta_pitch = np.arctan2(X, Z)

            # 先判断地表距离是否在覆盖范围内
            # subpoint = wgs84.subpoint(geocentric)
            # sat_lat = subpoint.latitude.degrees
            # sat_lon = subpoint.longitude.degrees
            # surface_dist = self.haversine_distance(sat_lat, sat_lon, lat, lon)
            # print("卫星位置：", sat_lat, sat_lon, "目标位置：", lat, lon, "距离：", surface_dist)
            # 检查角度限制和地球遮挡
            if (abs(theta_roll) <= theta_roll_max) and (abs(theta_pitch) <= theta_pitch_max):
                is_visible = True
                break
                # 目标可见，更新或创建时间窗口
        if is_visible:
            if self.down_window is None:
                self.down_window = [t.utc_datetime(), t.utc_datetime()]
            else:
                self.down_window[1] = t.utc_datetime()
        elif self.down_window:
            self.downlink_windows.append(self.down_window)
            self.down_window = None

    # def calculate_down_window(self, now_time, geocentric):
    #     """
    #     动态计算数传时间窗口
    #     :param now_time:    当前时间
    #     :param geocentric: 卫星当前时刻的地心坐标
    #     :return:
    #     """
    #     theta_roll_max = np.radians(self.side_swing_angle_Max)
    #     theta_pitch_max = np.radians(self.pitch_angle_Max)
    #     is_visible = False
    #     for lat, lon in [(29, 106), (38, 115), (47, 123), (19, 110), (47, 130), (39, 75)]:
    #         transformer = Transformer.from_crs("EPSG:4326", "EPSG:4978")
    #         x_g, y_g, z_g = transformer.transform(lat, lon, 0)
    #         P_ground_ECEF = np.array([x_g, y_g, z_g])
    #         t = now_time  # 获取时间点
    #         P_sat_ECI = geocentric.position.km  # 卫星ECI坐标
    #         V_sat_ECI = geocentric.velocity.km_per_s  # 卫星速度矢量
    #         # 地球自转修正：ECEF → ECI
    #         P_ground_ECI = self.earth_rotation_matrix(t) @ P_ground_ECEF
    #         # 计算 LVLH 坐标系（Local Vertical, Local Horizontal）
    #         # Z轴指向地心
    #         Z_lvlh = -P_sat_ECI / np.linalg.norm(P_sat_ECI)
    #         # Y轴垂直于轨道平面
    #         Y_lvlh = np.cross(P_sat_ECI, V_sat_ECI)
    #         Y_lvlh = Y_lvlh / np.linalg.norm(Y_lvlh)
    #         # X轴完成右手坐标系
    #         X_lvlh = np.cross(Y_lvlh, Z_lvlh)
    #
    #         # 构建旋转矩阵（ECI到LVLH的坐标变换）
    #         R_ECI_to_LVLH = np.vstack([X_lvlh, Y_lvlh, Z_lvlh])
    #
    #         # 计算地面目标相对于卫星的矢量（ECI坐标系）
    #         vec_target_ECI = P_ground_ECI - P_sat_ECI
    #
    #         # 将目标矢量转换到LVLH坐标系
    #         vec_target_LVLH = R_ECI_to_LVLH @ vec_target_ECI
    #         X, Y, Z = vec_target_LVLH
    #
    #         # 计算侧视角与俯仰角
    #         theta_roll = np.arctan2(Y, Z)
    #         theta_pitch = np.arctan2(X, Z)
    #         if (abs(theta_roll) <= theta_roll_max) and (abs(theta_pitch) <= theta_pitch_max):
    #             is_visible = True
    #             break
    #             # 目标可见，更新或创建时间窗口
    #     if is_visible:
    #         if self.down_window is None:
    #             self.down_window = [t.utc_datetime(), t.utc_datetime()]
    #         else:
    #             self.down_window[1] = t.utc_datetime()
    #     elif self.down_window:
    #         self.downlink_windows.append(self.down_window)
    #         self.down_window = None

    def simple_window(self, task):
        task.visible_windows[self.sat_name] = [[task.earliest_start_time, task.latest_end_time]]

    def calculate_time_windows(self, task):
        """
        计算任务对应的可见性时间窗口
        """
        # 将角度限制转换为弧度
        theta_roll_max = np.radians(self.side_swing_angle_Max)
        theta_pitch_max = np.radians(self.pitch_angle_Max)

        # 获取目标位置的经纬度
        lat, lon = task.target_location

        # 地面点坐标转换（WGS84经纬度 → ECEF）
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:4978")
        x_g, y_g, z_g = transformer.transform(lat, lon, 0)
        P_ground_ECEF = np.array([x_g, y_g, z_g])
        ts = load.timescale()
        windows = []
        # 使用初始化时计算的轨道覆盖范围
        d_max = self.d_max

        # print("卫星：", self.sat_name, "最大地面覆盖距离：", d_max)

        i = 0
        while i < len(self.sat_trace):
            item = self.sat_trace[i]
            t = item[1]  # 获取时间点
            P_sat_ECI = item[0].position.km  # 卫星ECI坐标
            V_sat_ECI = item[0].velocity.km_per_s  # 卫星速度矢量

            # 先判断地表距离是否在覆盖范围内
            subpoint = wgs84.subpoint(item[0])
            sat_lat = subpoint.latitude.degrees
            sat_lon = subpoint.longitude.degrees
            surface_dist = self.haversine_distance(sat_lat, sat_lon, lat, lon)
            # print("卫星位置：", sat_lat, sat_lon, "目标位置：", lat, lon, "距离：", surface_dist)
            if surface_dist > d_max:
                i += 1
                # print("不在覆盖范围", surface_dist, task.target_location, sat_lat, sat_lon)
                continue

            # print("在覆盖范围", surface_dist)

            if np.any(np.isnan(P_ground_ECEF)) or np.any(np.isinf(P_ground_ECEF)):
                print("异常P_ground_ECEF:", P_ground_ECEF, "对应时间t:", t)
                print("任务id：", task.task_id, "任务位置：", task.target_location)

            # 地球自转修正：ECEF → ECI
            P_ground_ECI = self.earth_rotation_matrix(t) @ P_ground_ECEF

            # 地球遮挡判断
            # if self.check_earth_occlusion(P_sat_ECI, P_ground_ECI):
            #     print("被遮挡了")
            #     i += 1
            #     continue

            # 计算 LVLH 坐标系（只计算一次）
            Z_lvlh = -P_sat_ECI / np.linalg.norm(P_sat_ECI)
            Y_lvlh = np.cross(P_sat_ECI, V_sat_ECI)
            Y_lvlh = Y_lvlh / np.linalg.norm(Y_lvlh)
            X_lvlh = np.cross(Y_lvlh, Z_lvlh)

            # 构建旋转矩阵
            R_ECI_to_LVLH = np.vstack([X_lvlh, Y_lvlh, Z_lvlh])
            #
            # # 计算地面目标相对于卫星的矢量
            # vec_target_ECI = P_ground_ECI - P_sat_ECI
            # vec_target_LVLH = R_ECI_to_LVLH @ vec_target_ECI
            # X, Y, Z = vec_target_LVLH

            # 计算侧视角与俯仰角
            # theta_roll = np.arctan2(Y, Z) # 计算侧视角
            # theta_pitch = np.arctan2(X, Z)  # 计算俯仰角

            # 判定可见性（角度限制）
            # if abs(theta_pitch) <= theta_pitch_max:
            # if (abs(theta_roll) <= theta_roll_max) and (abs(theta_pitch) <= theta_pitch_max):
            # 计算地心在卫星坐标系中的位置（地心到卫星的向量）
            vec_earth_sat_LVLH = -P_sat_ECI  # 在ECI中，地心到卫星的向量就是卫星位置的负值
            vec_earth_sat_LVLH = R_ECI_to_LVLH @ vec_earth_sat_LVLH

            # 计算任务点在卫星坐标系中的位置（地心到任务的向量）
            vec_earth_target_LVLH = P_ground_ECI - P_sat_ECI  # 在ECI中，地心到任务的向量
            vec_earth_target_LVLH = R_ECI_to_LVLH @ vec_earth_target_LVLH

            # 计算两个向量的夹角
            cos_angle = np.dot(vec_earth_sat_LVLH, vec_earth_target_LVLH) / (
                    np.linalg.norm(vec_earth_sat_LVLH) * np.linalg.norm(vec_earth_target_LVLH))
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))

            # 计算卫星的角速度
            angular_velocity = np.linalg.norm(V_sat_ECI) / np.linalg.norm(P_sat_ECI)

            # 计算时间窗口长度（2倍夹角除以角速度）
            window_duration = 2 * angle / angular_velocity

            # 创建时间窗口
            start_time = t.utc_datetime()
            start_time = start_time.replace(tzinfo=timezone.utc)
            end_time = (start_time + timedelta(seconds=window_duration)).replace(microsecond=0)
            window = [start_time, end_time]

            # 判断是否满足可见性条件
            if task.sensor_type == "optical" or task.sensor_type == "infrared":
                if task.cloud_thickness <= self.cloud_threshold:
                    if task.sensor_type == "infrared":
                        windows.append(window)
                    elif task.check_illumination(ts.utc(start_time)) and task.check_illumination(ts.utc(end_time)):
                        windows.append(window)
            else:
                windows.append(window)
            # 跳过时间窗口内的轨迹点
            skip_steps = int(window_duration / self.interval_time) + 1
            i += skip_steps
                # i += 1
            # else:
            #     i += 1

        if windows:
            task.visible_windows[self.sat_name] = windows

    # def check_earth_occlusion(self, satellite_position, target_position):
    #     """
    #     判断卫星与目标点是否被地球遮挡
    #
    #     参数:
    #     satellite_position: 卫星位置向量 (ECI坐标系，km)
    #     target_position: 目标点位置向量 (ECI坐标系，km)
    #
    #     返回:
    #     bool: True表示被地球遮挡，False表示未被遮挡
    #     """
    #
    #     # 向量 A: 目标点位置 (g) 到卫星位置 (s)
    #     A = np.array(satellite_position) - np.array(target_position)
    #     # 向量 B: 目标点位置 (g) 到地心 (O)
    #     B = -np.array(target_position)
    #
    #     # 计算投影参数 t
    #     t = np.dot(A, B)
    #     print("t", t)
    #     # 如果 t 在 [0, 1] 范围内，说明垂足在线段 gs 上
    #     if 0 < t:
    #         return True
    #         # # 计算垂足到地心的距离 d
    #         # d = np.linalg.norm(B - t * A)
    #         # print("d", d)
    #         # return d < 6371
    #     # 若 t < 0 ，无遮挡
    #     return False
    #
    # def test_earth_occlusion(self):
    #     """
    #     测试地球遮挡判断函数
    #     """
    #     print("=== 开始地球遮挡测试 ===")
    #
    #     # 测试用例1：卫星在地球上方，目标在地球表面，应该无遮挡
    #     print("\n--- 测试1: 卫星在目标正上方 ---")
    #     sat_pos1 = np.array([0, 0, 7000])  # 卫星在7000km高度
    #     target_pos1 = np.array([6371, 0, 0])  # 目标在地球表面
    #     result1 = self.check_earth_occlusion(sat_pos1, target_pos1)
    #     print(f"结果: {'无遮挡' if not result1 else '有遮挡'} (期望: 无遮挡)")
    #
    #     # 测试用例2：卫星和目标都在地球表面，应该无遮挡（特殊情况）
    #     print("\n--- 测试2: 卫星和目标都在地球表面 ---")
    #     sat_pos2 = np.array([6371, 0, 0])
    #     target_pos2 = np.array([6371, 1000, 0])
    #     result2 = self.check_earth_occlusion(sat_pos2, target_pos2)
    #     print(f"结果: {'无遮挡' if not result2 else '有遮挡'} (期望: 无遮挡)")
    #
    #     # 测试用例3：卫星在地球一侧，目标在地球另一侧，应该有遮挡
    #     print("\n--- 测试3: 卫星和目标在地球两侧 ---")
    #     sat_pos3 = np.array([8000, 0, 0])
    #     target_pos3 = np.array([-8000, 0, 0])
    #     result3 = self.check_earth_occlusion(sat_pos3, target_pos3)
    #     print(f"结果: {'无遮挡' if not result3 else '有遮挡'} (期望: 有遮挡)")
    #
    #     # 测试用例4：卫星在低轨道，目标在地球另一侧，应该有遮挡
    #     print("\n--- 测试4: 低轨道卫星 ---")
    #     sat_pos4 = np.array([7000, 0, 0])  # 低轨道卫星
    #     target_pos4 = np.array([-7000, 0, 0])  # 地球另一侧的目标
    #     result4 = self.check_earth_occlusion(sat_pos4, target_pos4)
    #     print(f"结果: {'无遮挡' if not result4 else '有遮挡'} (期望: 有遮挡)")
    #
    #     print("\n=== 测试完成 ===")

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        计算两个经纬度点之间的距离
        """
        # 输入为度，输出为km
        R = 6378  # 地球半径，单位km
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c

    def earth_rotation_matrix(self, t):
        """
        计算地球自转矩阵，用于ECEF到ECI的坐标转换

        参数:
        t: skyfield时间对象

        返回:
        旋转矩阵(3x3)
        """
        try:
            # 计算地球旋转角度
            # 地球自转角速度 (rad/s)
            omega = 7.2921159e-5

            # 获取儒略日
            julian_day = t.tt
            if np.isnan(julian_day) or np.isinf(julian_day):
                raise ValueError("Invalid Julian day value")

            # 计算格林尼治恒星时 (GMST)
            T = (julian_day - 2451545.0) / 36525.0  # 儒略世纪数
            if np.isnan(T) or np.isinf(T):
                raise ValueError("Invalid T value")

            # 使用更稳定的计算方法
            gmst = 280.46061837 + 360.98564736629 * (
                    julian_day - 2451545.0) + 0.000387933 * T ** 2 - T ** 3 / 38710000.0
            gmst = gmst % 360  # 确保在0-360度范围内
            gmst = np.radians(gmst)  # 转换为弧度

            # 绕Z轴的旋转矩阵
            cos_angle = np.cos(gmst)
            sin_angle = np.sin(gmst)

            # ECEF到ECI的旋转矩阵
            rotation_matrix = np.array([
                [cos_angle, sin_angle, 0],
                [-sin_angle, cos_angle, 0],
                [0, 0, 1]
            ])

            # 检查矩阵是否包含无效值
            if np.any(np.isnan(rotation_matrix)) or np.any(np.isinf(rotation_matrix)):
                raise ValueError("Invalid values in rotation matrix")

            return rotation_matrix
        except Exception as e:
            print(f"Error in earth_rotation_matrix: {e}")
            # 返回单位矩阵作为默认值
            return np.eye(3)

    def execute_satellite_tasks(self, task, START_TIME, time_steps, imageloader):
        """
        执行卫星任务,与卫星网络的check_execute_tasks配套
        """
        img_path = imageloader.get_random_image_path()
        # 选择载荷执行任务
        if self.star_payload == task.sensor_type and self.status == "FREE":
            self.running_task = task.task_id
            print(f"卫星 {self.sat_name} 执行任务: {task.task_id}")
            self.status = "BUSY"

            self.side_swing_angle = task.side_swing_angle
            print(f"执行载荷任务: {task.task_id}, 类型: {task.sensor_type}, 执行时间: {task.execution_time}秒")
            try:
                task.execution_time = float(task.execution_time)
            except ValueError:
                print(f"错误： 不能转换为浮点数,默认执行5秒")
                task.execution_time = 5.0
            # 使用任务指定的执行时间
            time.sleep(task.execution_time)

            # 生成任务结果
            result = {
                "task_id": task.task_id,
                "sensor_type": self.star_payload,
                "execution_time": task.execution_time,
                "completion_time": time.time(),
                "data": img_path
            }

            task.FINISHED = True
            self.running_task = None
            # 将任务的结果发送到结果队列
            self.result_list.append(result)
            self.status = "FREE"

            return True
        return False

    def angle_turn(self):
        """
        角度姿态调整
        :return:
        """
        pass

    def current_time_func(self, START_TIME, time_steps):
        """
        根据时间步计算从Start_Time开始的当前时间（使用datetime库自动处理进位）
        @param time_steps: 时间步（秒数）
        @return: 从Start_Time开始的当前时间（skyfield时间对象）
        """
        ts = load.timescale()

        # 添加时间差（自动处理进位）
        new_datetime = START_TIME + timedelta(seconds=time_steps)

        # 转换为skyfield的UTC时间格式
        current_time = ts.utc(
            new_datetime.year,
            new_datetime.month,
            new_datetime.day,
            new_datetime.hour,
            new_datetime.minute,
            new_datetime.second
        )
        return current_time

    # def current_time_func(self, START_TIME, time_steps):
    #     """
    #     根据时间步计算从Start_Time开始的当前时间
    #     @param time_steps:时间步
    #     @return:从Start_Time开始的当前时间
    #     """
    #     ts = load.timescale()
    #     second = START_TIME[5] + time_steps
    #     minute = START_TIME[4] + second // 60
    #     hour = START_TIME[3] + minute // 60
    #     day = START_TIME[2] + hour // 24
    #     current_time = ts.utc(START_TIME[0], START_TIME[1], day,
    #                           hour % 24, minute % 60, second % 60)
    #     return current_time

    # def ground_station_time_windows(self, ground_station_lat, ground_station_lon, min_elevation=10):
    #     """
    #     计算卫星过顶地面站的时间窗口
    #     :param ground_station_lat: 地面站纬度
    #     :param ground_station_lon: 地面站经度
    #     :param min_elevation: 最小仰角（度），默认10度
    #     :return: 时间窗口列表，每个窗口包含[开始时间, 结束时间]
    #     """
    #     # 将地面站位置转换为WGS84坐标
    #     ground_station = wgs84.latlon(ground_station_lat, ground_station_lon)
    #
    #     # 将最小仰角转换为弧度
    #     min_elevation_rad = min_elevation * np.pi / 180
    #
    #     # 存储时间窗口
    #     time_windows = []
    #     current_window = None
    #
    #     # 遍历卫星轨迹
    #     for trace_point in self.sat_trace:
    #         # 获取卫星位置和时间
    #         sat_pos = trace_point[1].position.km
    #         current_time = trace_point[0]
    #
    #         # 计算卫星到地面站的向量
    #         gs_vector = np.array(ground_station.itrs_xyz.km) - np.array(sat_pos)
    #
    #         # 计算卫星到地心的向量
    #         earth_center_vector = -np.array(sat_pos)
    #
    #         # 计算仰角
    #         cos_elevation = np.dot(gs_vector, earth_center_vector) / (
    #                 np.linalg.norm(gs_vector) * np.linalg.norm(earth_center_vector))
    #         elevation = np.arccos(np.clip(cos_elevation, -1.0, 1.0))
    #
    #         # 检查是否满足最小仰角要求
    #         if elevation >= min_elevation_rad:
    #             if current_window is None:
    #                 # 开始新的时间窗口
    #                 current_window = [current_time, current_time]
    #             else:
    #                 # 更新当前时间窗口的结束时间
    #                 current_window[1] = current_time
    #         else:
    #             if current_window is not None:
    #                 # 保存当前时间窗口
    #                 time_windows.append(current_window)
    #                 current_window = None
    #
    #     if current_window is not None:
    #         time_windows.append(current_window)
    #
    #     return time_windows

    # def run(self, state_dict):
    #     """
    #     卫星线程运行函数
    #     """
    #     print(f"卫星 {self.sat_name} 线程启动")
    #
    #     while True:
    #         # 更新状态
    #         current_state = self.update_state()
    #         state_dict[self.sat_name] = current_state
    #
    #         # 执行任务
    #         # self.execute_satellite_task()
    #
    #         time.sleep(0.5)  # 控制更新频率

    # 模拟太阳能充电
    def charge(self, time_point=None):
        """
        计算卫星与太阳的相对位置，判断是否能进行太阳能充电
        :return:
        """
        try:
            # 加载星历数据和时间尺度
            ts = load.timescale()
            # 使用时自动加载
            planets = load('./library/de421.bsp')
            earth = planets['earth']
            sun = planets['sun']

            # 计算当前时间或指定时间
            t = time_point if time_point is not None else ts.now()  # 可替换为具体时间，如 ts.utc(2025, 3, 29, 12, 0)

            # 获取太阳位置（相对于地球）
            sun_pos = earth.at(t).observe(sun).position.km

            # 获取卫星位置（相对于地球）
            sat_geocentric = self.sat_model.at(t)
            sat_pos = sat_geocentric.position.km

            # 地球半径km
            R_earth = 6371.0

            # 计算太阳位置向量和卫星位置向量
            S = sun_pos  # 太阳位置向量
            P = sat_pos  # 卫星位置向量

            # 计算投影长度d（卫星在地日连线上的投影）
            d = np.dot(P, S) / np.linalg.norm(S)

            # 计算卫星到地日连线的垂直距离h
            h = np.linalg.norm(np.cross(P, S)) / np.linalg.norm(S)

            # 判断是否处于阴影中
            in_shadow = (d < 0) and (h < R_earth)

            return not in_shadow  # 返回是否能充电（不在阴影中）
        except Exception as e:
            print(f"计算充电状态时出错: {e}")
            # 默认假设可以充电
            return True

    def check_geo_coverage(self, geocentric):
        """
        检查卫星是否在GEO卫星的覆盖范围内，并更新连接的高轨卫星
        :param geocentric: 卫星的地心坐标
        """
        # 获取卫星的经纬度
        subpoint = wgs84.subpoint(geocentric)
        sat_longitude = subpoint.longitude.degrees

        # 计算到每个GEO卫星的经度差，找出最近的
        min_diff = float('inf')
        nearest_geo = None

        for geo_name, geo_sat in self.geo_satellites.items():
            # 计算经度差（考虑经度环绕）
            longitude_diff = abs(sat_longitude - geo_sat['longitude'])
            longitude_diff = min(longitude_diff, 360 - longitude_diff)

            # 更新最近的GEO卫星
            if longitude_diff < min_diff:
                min_diff = longitude_diff
                nearest_geo = geo_name

        # 由于GEO卫星的覆盖角度为120度，且均匀分布，所以一定能覆盖所有地表
        self.is_connect_geo = True
        self.connecting_geo = nearest_geo

    def calculate_orbital_altitude(self):
        """
        通过TLE计算卫星的轨道高度
        :return: 轨道高度（km）
        """
        try:
            # 首先尝试使用skyfield库计算
            from skyfield.api import EarthSatellite, load
            from skyfield.earthlib import earthradius_km

            # 创建卫星对象
            satellite = EarthSatellite(self.tle_line1, self.tle_line2)

            # 获取轨道半长轴
            semi_major_axis_km = satellite.model.a * earthradius_km

            # 估算平均轨道高度（半长轴减去地球半径）
            orbit_height = semi_major_axis_km - earthradius_km

            # print(f"卫星 {self.sat_name} 轨道高度 (skyfield): {orbit_height:.2f} km")
            return orbit_height

        except Exception as e1:
            try:
                # 尝试使用sgp4库计算
                from sgp4.earth_gravity import wgs72
                from sgp4.io import twoline2rv

                satellite = twoline2rv(self.tle_line1, self.tle_line2, wgs72)

                # 计算轨道半长轴（千米）
                semi_major_axis_km = satellite.a * 6378.137

                # 估算平均轨道高度
                orbit_height = semi_major_axis_km - 6378.137  # 减去地球平均半径

                # print(f"卫星 {self.sat_name} 轨道高度 (sgp4): {orbit_height:.2f} km")
                return orbit_height

            except Exception as e2:
                try:
                    # 最后尝试使用现有的sat_model
                    if self.sat_model is not None:
                        # 地球半径（km）
                        R_earth = 6378.0

                        # 使用当前时间计算卫星位置
                        ts = load.timescale()
                        current_time = ts.now()

                        # 获取卫星位置
                        geocentric = self.sat_model.at(current_time)
                        sat_position = geocentric.position.km

                        # 计算轨道高度（卫星到地心的距离减去地球半径）
                        orbital_radius = np.linalg.norm(sat_position)
                        altitude = orbital_radius - R_earth

                        # print(f"卫星 {self.sat_name} 轨道高度 (sat_model): {altitude:.2f} km")
                        return altitude
                    else:
                        raise Exception("sat_model为空")

                except Exception as e3:
                    print(f"计算卫星 {self.sat_name} 轨道高度时出错:")
                    print(f"  skyfield错误: {e1}")
                    print(f"  sgp4错误: {e2}")
                    print(f"  sat_model错误: {e3}")
                    print("使用默认高度550km")
                    return 550.0

    def save_data(self, data, filename):
        """保存轨迹数据"""
        with open(filename, 'wb') as f:
            pickle.dump(data, f)

    def load_data(self, filename):
        """从文件读取轨迹数据"""
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                return pickle.load(f)
        return None  # 或返回默认值
