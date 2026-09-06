import math
import uuid
from datetime import datetime, timezone, timedelta

import numpy as np
from Service.TaskService import Task
from Service.SatelliteService import Satellite


def calculate_region_center_and_orientation(boundary_points):
    """
    计算区域的重心和主要方向
    """
    # 计算重心
    center_lat = sum(point[0] for point in boundary_points) / len(boundary_points)
    center_lon = sum(point[1] for point in boundary_points) / len(boundary_points)

    # 计算协方差矩阵
    points_array = np.array(boundary_points)
    centered_points = points_array - np.array([center_lat, center_lon])
    covariance_matrix = np.cov(centered_points.T)

    # 计算特征值和特征向量
    eigenvalues, eigenvectors = np.linalg.eigh(covariance_matrix)

    # 主要方向（最大特征值对应的特征向量）
    main_direction = eigenvectors[:, np.argmax(eigenvalues)]

    return (center_lat, center_lon), main_direction, eigenvalues


def split_area_target_into_point_targets(task, satellites=None):
    """
    将多边形区域目标拆分成多个点目标，使用自适应网格
    Args:
    satellites: 卫星的列表
    task: 任务对象
    :return: 点目标列表
    """
    # 找出所有卫星中最小的扫幅
    min_swath = min(satellite.width_of_cloth for satellite in satellites) if satellites else 50

    # 获取区域目标的边界点数组
    boundary_points = task.boundary_points

    # 计算区域的重心和主要方向
    center, main_direction, eigenvalues = calculate_region_center_and_orientation(boundary_points)

    # 计算区域的形状特征
    aspect_ratio = math.sqrt(eigenvalues[1] / eigenvalues[0]) if eigenvalues[0] != 0 else 1

    # 计算区域边界
    min_lat = min(point[0] for point in boundary_points)
    max_lat = max(point[0] for point in boundary_points)
    min_lon = min(point[1] for point in boundary_points)
    max_lon = max(point[1] for point in boundary_points)

    # 计算区域面积
    area_width = (max_lon - min_lon) * 111 * math.cos(math.radians((min_lat + max_lat) / 2))
    area_height = (max_lat - min_lat) * 111
    total_area = area_width * area_height

    # 根据区域形状和面积确定点目标数量`
    base_points = max(4, min(20, int(total_area / (min_swath * min_swath))))

    # 针对细长区域的特殊处理
    if aspect_ratio > 2:  # 细长区域
        # 限制细长区域的最大点目标数量
        target_points = min(base_points, 10)
        # 根据长宽比调整网格划分
        lat_grids = 2  # 细长区域在短边方向使用较少的网格
        lon_grids = int(target_points / lat_grids)
    else:  # 接近正方形区域
        target_points = base_points
        lat_grids = lon_grids = int(math.sqrt(target_points))

    lat_grid_size = (max_lat - min_lat) / lat_grids
    lon_grid_size = (max_lon - min_lon) / lon_grids

    # 创建网格点
    point_targets = []
    count = 0

    # 从中心向外扩展生成点
    center_lat, center_lon = center
    for i in range(-lat_grids // 2, lat_grids // 2 + 1):
        for j in range(-lon_grids // 2, lon_grids // 2 + 1):
            lat = center_lat + i * lat_grid_size
            lon = center_lon + j * lon_grid_size

            # 检查点是否在多边形内
            if is_point_in_polygon((lat, lon), boundary_points):
                count += 1
                subtask_id = task.task_id * 10000 + count
                point_target = Task(
                    task_id=subtask_id,
                    task_name=task.task_name,
                    sensor_type=task.sensor_type,
                    target_location=[round(lat, 2), round(lon, 2)],
                    cluster_name=task.cluster_name,
                    latest_end_time=task.latest_end_time,
                    earliest_start_time=task.earliest_start_time,
                    resolution=task.resolution,
                    priority=task.priority,
                    boundary_points=None,
                    is_emergency=task.is_emergency,
                    task_type='点目标',
                    parent_task_id=task.task_id,
                    cloud_thickness=task.cloud_thickness,
                    parent_location=task.target_location,
                    parent_type=task.task_type
                )
                task.subtasks.append(point_target)
                task.subtask_ids.append(subtask_id)
                point_targets.append(point_target)

    return point_targets


def is_point_in_polygon(point, polygon):
    """
    判断点是否在多边形内

    参数:
    point: 待判断的点 (lat, lon)
    polygon: 多边形的顶点数组 [(lat1, lon1), (lat2, lon2), ...]

    返回:
    bool: 点是否在多边形内
    """
    # 使用射线法判断点是否在多边形内
    x, y = point[0], point[1]
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    # xinters 仅在边非水平（p1y != p2y）时有效，避免引用未定义/陈旧值
                    xinters = None
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or (xinters is not None and x <= xinters):
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def split_cycle_target_into_point_targets(task):
    """
    将周期目标拆分成多个点目标

    参数:
    task: 周期目标对象

    返回:
    list: 点目标列表
    """
    interval = task.latest_end_time - task.earliest_start_time
    count = interval.total_seconds() // task.cycle_time
    for i in range(int(count)):
        start_time = task.earliest_start_time + i * timedelta(seconds=task.cycle_time)
        end_time = task.earliest_start_time + (i + 1) * timedelta(seconds=task.cycle_time)
        subtask_id = task.task_id * 10000 + i + 1
        point_target = Task(
            task_id=subtask_id,
            task_name=task.task_name,
            sensor_type=task.sensor_type,
            target_location=task.target_location,
            cluster_name=task.cluster_name,
            latest_end_time=end_time,
            earliest_start_time=start_time,
            resolution=task.resolution,
            priority=task.priority,
            boundary_points=None,
            is_emergency=task.is_emergency,
            task_type='点目标',
            parent_task_id=task.task_id,
            cloud_thickness=task.cloud_thickness,
            parent_location=task.target_location,
            parent_type=task.task_type
        )
        task.subtasks.append(point_target)
        task.subtask_ids.append(subtask_id)
    return task.subtasks


# class Satellite:
#     def __init__(self, width_of_cloth):
#         self.width_of_cloth = width_of_cloth


if __name__ == '__main__':
    pass
    # print("This module should be imported and used as a function.")
    #
    # # 测试用例1：不规则五边形
    # task1 = Task(
    #     task_id=1,
    #     sensor_type="红外",
    #     target_location=None,
    #     cluster_name="Cluster1",
    #     latest_end_time="2023-01-01",
    #     earliest_start_time="2023-01-01",
    #     resolution=0.5,
    #     priority=1,
    #     boundary_points=[
    #         (37.46, 119.2),  # 左下
    #         (42.0, 115.0),  # 左上
    #         (45.0, 125.0),  # 顶部
    #         (40.0, 135.0),  # 右上
    #         (35.0, 130.0),  # 右下
    #     ],
    #     is_emergency=False,
    #     task_type="区域目标",
    #     parent_task_id=None,
    # )
    #
    # # 测试用例2：细长区域
    # task2 = Task(
    #     task_id=2,
    #     sensor_type="红外",
    #     target_location=None,
    #     cluster_name="Cluster1",
    #     latest_end_time="2023-01-01",
    #     earliest_start_time="2023-01-01",
    #     resolution=0.5,
    #     priority=1,
    #     boundary_points=[
    #         (37.46, 119.2),  # 左下
    #         (37.46, 150.0),  # 左上
    #         (38.0, 150.0),  # 右上
    #         (38.0, 119.2),  # 右下
    #     ],
    #     is_emergency=False,
    #     task_type="区域目标",
    #     parent_task_id=None,
    # )
    #
    # satellites = [Satellite(width_of_cloth=100), Satellite(width_of_cloth=100)]
    #
    # print("\n测试不规则五边形区域：")
    # tasks1 = split_area_target_into_point_targets(task1, satellites)
    # print(f"生成的点目标数量: {len(tasks1)}")
    # for task in tasks1:
    #     print(f"点目标位置: {task.target_location}")
    #
    # print("\n测试细长区域：")
    # tasks2 = split_area_target_into_point_targets(task2, satellites)
    # print(f"生成的点目标数量: {len(tasks2)}")
    # for task in tasks2:
    #     print(f"点目标位置: {task.target_location}")
    # task1 = Task(
    #     task_id=1,
    #     sensor_type="optical",
    #     target_location=[37.46, 119.2],
    #     cluster_name="Cluster1",
    #     earliest_start_time=datetime.strptime("2021-05-10 00:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc),
    #     latest_end_time=datetime.strptime("2021-05-11 00:00:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc),
    #     resolution=0.5,
    #     priority=1,
    #     boundary_points=None,
    #     is_emergency=False,
    #     task_type="周期观测",
    #     parent_task_id=None,
    # )
    #
    # split_cycle_target_into_point_targets(task1)
