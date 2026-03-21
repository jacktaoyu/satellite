import pandas as pd
from Service.task_scheduling import SatelliteScheduler, Task, Satellite


def exportcfuc(tasks, satellites, start_time, end_time):
    task_array = []
    satellite_array = []

    # 处理任务数据
    task_data = []
    for task in tasks:
        task1 = Task(
            task_id=task.task_id,
            cluster_names=task.cluster_name,
            task_type=task.task_type,
            priority=task.priority,
            target_location=task.target_location,
            sensor_type=task.sensor_type,
            resolution=task.resolution,
            earliest_start_time=task.earliest_start_time,
            latest_end_time=str(task.latest_end_time),
            visible_windows=str(task.visible_windows)
        )
        # 打印任务属性
        print(f"任务 ID: {task1.task_id}")
        print(f"集群名称: {task1.cluster_names}")
        print(f"任务类型: {task1.task_type}")
        print(f"优先级: {task1.priority}")
        print(f"目标位置: {task1.target_location}")
        print(f"传感器类型: {task1.sensor_type}")
        print(f"分辨率: {task1.resolution}")
        print(f"最早开始时间: {task1.earliest_start_time}")
        print(f"最晚结束时间: {task1.latest_end_time}")
        print(f"可见窗口: {task1.visible_windows}")
        print("-" * 50)
        task_array.append(task1)
        task_data.append([
            task1.task_id, task1.cluster_names, task1.task_type, task1.priority,
            task1.target_location, task1.sensor_type, task1.resolution,
            task1.earliest_start_time, task1.latest_end_time, task1.visible_windows
        ])

    # 处理卫星数据
    satellite_data = []
    for satellite in satellites:
        sat = Satellite(
            cluster_names=satellite.belong_cluster,
            sat_id=satellite.sat_name,
            sensor_type=satellite.star_payload,
            tle_line1=satellite.tle_line1,
            tle_line2=satellite.tle_line2,
            resolution_capability=satellite.resolution_capability,
            battery_capacity=satellite.battery_capacity,
            data_storage=satellite.max_storage,
            imaging_speed=satellite.imaging_speed,
            downlink_windows=satellite.downlink_windows,
            charging_windows=satellite.charging_windows
        )
        # 打印卫星属性
        print(f"卫星 ID: {sat.sat_id}")
        print(f"集群名称: {sat.cluster_names}")
        print(f"传感器类型: {sat.sensor_type}")
        print(f"TLE 行 1: {sat.tle_line1}")
        print(f"TLE 行 2: {sat.tle_line2}")
        print(f"分辨率能力: {sat.resolution_capability}")
        print(f"电池容量: {sat.battery_capacity}")
        print(f"数据存储: {sat.data_storage}")
        print(f"成像速度: {sat.imaging_speed}")
        print(f"下行链路窗口: {sat.downlink_windows}")
        print(f"充电窗口: {sat.charging_windows}")
        print("-" * 50)
        satellite_array.append(sat)
        satellite_data.append([
            sat.sat_id, sat.cluster_names, sat.sensor_type, sat.tle_line1,
            sat.tle_line2, sat.resolution_capability, sat.battery_capacity,
            sat.data_storage, sat.imaging_speed, sat.downlink_windows, sat.charging_windows
        ])

    # 保存到 Excel
    task_df = pd.DataFrame(task_data, columns=[
        '任务 ID', '集群名称', '任务类型', '优先级',
        '目标位置', '传感器类型', '分辨率',
        '最早开始时间', '最晚结束时间', '可见窗口'
    ])
    satellite_df = pd.DataFrame(satellite_data, columns=[
        '卫星 ID', '集群名称', '传感器类型', 'TLE 行 1',
        'TLE 行 2', '分辨率能力', '电池容量',
        '数据存储', '成像速度', '下行链路窗口', '充电窗口'
    ])

    with pd.ExcelWriter('tasks_and_satellites.xlsx') as writer:
        task_df.to_excel(writer, sheet_name='Tasks', index=False)
        satellite_df.to_excel(writer, sheet_name='Satellites', index=False)

    scheduler = SatelliteScheduler(task_array, satellite_array, start_time, end_time, algorithm="ant_colony")
    schedule = scheduler.solve(
        num_iterations=5,
        num_ants=10,
        evaporation_rate=0.1,
        alpha=1.0,
        beta=2.0,
        q0=0.5,
        local_search=True
    )
    return schedule
