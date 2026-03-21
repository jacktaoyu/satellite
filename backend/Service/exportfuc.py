import os
from Service.task_scheduling import Task, Satellite
from Service.Analyzer import SimplifiedSatelliteScheduler as Scheduler


def get_next_available_folder(base_path):
    """返回第一个可用的递增文件夹名"""
    i = 1
    while True:
        target_folder = os.path.join(base_path, str(i))
        if not os.path.exists(target_folder):
            return target_folder
        i += 1


def exportcfuc(tasks, satellites, start_time, end_time, completed_gravity, balance_gravity, priority_gravity):
    # completed_gravity 任务完成率权重
    # balance_gravity 负载均衡权重
    # priority_gravity 优先级权重
    task_array = []
    satellite_array = []

    # 处理任务数据
    for task in tasks:
        task1 = Task(
            task_id=task.task_id,  # 任务ID
            cluster_names=task.cluster_name,  # 所属星簇
            task_type=task.parent_type,  # 任务类型
            priority=task.priority,  # 优先级
            target_location=task.target_location,  # 目标位置
            sensor_type=task.sensor_type,  # 载荷类型
            resolution=task.resolution,  # 分辨率
            earliest_start_time=task.earliest_start_time,  # 最早开始时间
            latest_end_time=task.latest_end_time,  # 最晚结束时间
            visible_windows=task.visible_windows,  # 可见时间窗
            parent_task_id=task.parent_task_id,  # 父任务ID
            boundary_points=task.boundary_points,  # 边界点
            cloud_extent=task.cloud_thickness,  # 云层厚度
            task_name=task.task_name
        )
        task_array.append(task1)
        # print("任务类型:", task.task_id, task.task_type)
    # 处理卫星数据
    for satellite in satellites:
        imaging_powers = {'optical': 500, 'SAR': 1000, 'infrared': 700}
        imaging_powers[satellite.star_payload] = satellite.imaging_powers
        sat = Satellite(
            cluster_names=satellite.belong_cluster,
            sat_id=satellite.sat_name,
            sensor_type=satellite.star_payload,
            tle_line1=satellite.tle_line1,
            tle_line2=satellite.tle_line2,
            resolution_capability=satellite.resolution_capability,
            battery_capacity=satellite.battery_capacity,  # 电池容量
            initial_battery=satellite.battery,  # 初始当前电量
            data_storage=satellite.max_storage,  # 存储容量GB
            initial_storage=satellite.storage,  # 初始化当前存储
            # imaging_speed=satellite.imaging_speed,  # 成像速度（像素/秒）
            downlink_windows=satellite.downlink_windows,  # 下行时间窗
            charging_windows=satellite.charging_windows,  # 充电时间窗
            imaging_powers=imaging_powers,  # 成像功耗
            sunlight_powers={
                'maneuver': satellite.imaging_powers,  # 消耗功率（正值）
                'idle': satellite.eclipse_powers,  # 空闲消耗功率（正值）
                'charge': satellite.sunlight_powers  # 日照期功耗
            },
            eclipse_powers={
                'maneuver': satellite.maneuver_powers,  # 日食期间机动消耗（正值）
                'idle': satellite.eclipse_powers  # 日食期间空闲消耗（正值）
            },
            swath_width=satellite.width_of_cloth,  # 扫幅宽度，km
            max_slew_rate=satellite.angle_velocity,  # 最大转动速度
            downlink_rate=satellite.downlink_rate,  # 下行数据速率
            max_roll_angle=satellite.side_swing_angle_Max,  # 最大测摆角，整型，°
            max_pitch_angle=satellite.pitch_angle_Max,  # 最大俯仰角，整型，°
            tasks=[],
            payload_params=None
        )
        satellite_array.append(sat)
    scheduler = Scheduler(task_array, satellite_array, start_time, end_time, balance_gravity, priority_gravity,
                          completed_gravity)
    result = scheduler.run()
    if result is None:
        next_folder = get_next_available_folder("output_plans")
        os.makedirs(next_folder, exist_ok=True)
        return
    best_plan = scheduler.get_statistics('best')  # 综合最优方案
    current_display_schedule = best_plan['schedule']
    best_task_plan = scheduler.get_statistics('task')  # 任务满足率最优方案
    best_resource_plan = scheduler.get_statistics('resource')  # 资源利用率最高方案
    best_quality_plan = scheduler.get_statistics('quality')  # 成像质量最优方案
    algorithm_metrics = scheduler.algorithm_metrics
    # 示例：遗传算法参数(索引:遗传"genetic"、贪心"greedy"、蚁群"ant_colony")
    schedules = {
        "greedy_schedule": algorithm_metrics["greedy"]["schedule"],
        "genetic_schedule": algorithm_metrics["genetic"]["schedule"],
        "ant_colony_schedule": algorithm_metrics["ant_colony"]["schedule"]
    }
    next_folder = get_next_available_folder("output_plans")
    os.makedirs(os.path.dirname(next_folder), exist_ok=True)
    scheduler.export_schedule(schedules["greedy_schedule"], "greedy", next_folder)  # 保存
    scheduler.export_schedule(schedules["genetic_schedule"], "genetic", next_folder)  # 保存
    scheduler.export_schedule(schedules["ant_colony_schedule"], "ant_colony", next_folder)  # 保存
    current_display_schedule = best_plan['schedule']
    current_display_schedule = scheduler.merge_schedule(current_display_schedule)
    # print(f"当前展示结果为{current_display_schedule}")

    # 示例：遗传算法参数(索引:遗传"genetic"、贪心"greedy"、蚁群"ant_colony")
    # genetic_metrics = {
    #     "task_satisfaction": algorithm_metrics["genetic"]["task_satisfaction"],
    #     "resource_utilization": algorithm_metrics["genetic"]["resource_utilization"],
    #     'overall_storage_cost':algorithm_metrics["genetic"]['overall_storage_cost'],#所有星簇卫星总存储消耗gb
    #      'overall_battery_cost': algorithm_metrics["genetic"]['overall_battery_cost']#所有星簇卫星电量消耗wh
    # }
    # statistics = {
    #     'algorithm':best_plan['algorithm'],
    #      'overall_storage_cost':best_plan['overall_storage_cost'],#所有星簇卫星总存储消耗gb
    #       'overall_battery_cost': best_plan['overall_battery_cost']#所有星簇卫星电量消耗wh
    #     'schedule': best_plan['schedule'],  # 方案,字典
    #     'undownlinked_tasks_count': best_plan['undownlinked_tasks_count'],  # 仿真时间结束时未能下行任务总量,数值
    #     'undownlinked_tasks': best_plan['undownlinked_tasks'],  # 各卫星未能下行任务：sat_id为索引的字典
    #     'completed_tasks': best_plan['completed_tasks'],  # 已分配任务数,数值
    #     'entry_tasks': best_plan['entry_tasks'],  # 受理任务数，数值
    #     'task_satisfaction': best_plan['task_satisfaction'],  # 任务满足率，数值
    #     'resource_utilization': best_plan['resource_utilization'],  # 资源利用率，数值
    #     'imaging_quality': best_plan['imaging_quality'],  # 成像质量，数值
    #      'cluster_status':best_plan['cluster_status']#best_plan['cluster_status']={'cluster_time_cost','cluster_battery_cost','cluster_storage_cost','cluster_tasks_count'}
    # }
    # 以best_plan为例
    # best_plan_storage_cost=best_plan['overall_storage_cost']#所有星簇卫星总存储消耗gb
    # best_plan_battery_cost = best_plan['overall_battery_cost']#所有星簇卫星电量消耗wh
    # cluster_status=best_plan['cluster_status']#
    # print(f"总存储消耗{best_plan_storage_cost}")
    # print(f"总电量消耗{best_plan_battery_cost}")
    # print(cluster_status['cluster_1']['cluster_time_cost'])#时间秒
    # # 示例: 获取并导出综合最优方案
    # best_schedule = best_plan['schedule']  # 综合最佳方案
    # scheduler.export_schedule(best_schedule, "综合最优", "output_plans")  # 保存
    # best_plan_undownlinked_tasks_count = best_plan['undownlinked_tasks_count']  # 这个方案未下行卫星总数
    # print(best_plan_undownlinked_tasks_count)
    # best_plan_undownlinked_tasks = best_plan['undownlinked_tasks']  # 各卫星未下行任务
    # for sat_id, stats in best_plan_undownlinked_tasks.items():
    #     print(f"卫星id:{sat_id},未下行任务:{stats}")
    #
    # best_completed_tasks = best_plan['completed_tasks']  # 完成调度的任务
    # print(best_completed_tasks)
    # best_entry_tasks = best_plan['entry_tasks']  # 受理的任务
    # print(best_entry_tasks)
    # best_plan_task_satisfaction = best_plan['task_satisfaction']  # 任务满足率
    # print(best_plan_task_satisfaction)
    # best_plan_task_resource_utilization = best_plan['resource_utilization']  # 资源利用率
    # print(best_plan_task_resource_utilization)
    # best_plan_task_imaging_quality = best_plan['imaging_quality']  # 成像质量
    # print(best_plan_task_imaging_quality)
    return best_plan, best_task_plan, best_resource_plan, best_quality_plan, algorithm_metrics, current_display_schedule
