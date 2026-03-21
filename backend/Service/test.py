import numpy as np
import datetime
from datetime import datetime, timedelta, timezone
import json
from task_scheduling import Task,Satellite
from Analyzer import SimplifiedSatelliteScheduler as Scheduler
def load_tasks(filename):
    """从JSON文件加载任务数据并转换为Task对象"""
    with open(filename, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)

    tasks = []
    for task_data in tasks_data:
        # 处理可见时间窗口
        visible_windows = {}
        if 'visible_windows' in task_data:
            for sat_id, windows in task_data['visible_windows'].items():
                # 将字符串时间转换为datetime对象
                visible_windows[sat_id] = [
                    (datetime.fromisoformat(start), datetime.fromisoformat(end))
                    for start, end in windows
                ]
        task = Task(
            task_id=task_data["task_id"],
            priority=task_data["priority"],
            target_location=tuple(task_data["target_location"]),
            sensor_type=task_data["sensor_type"],
            resolution=task_data["resolution"],
            earliest_start_time=datetime.fromisoformat(task_data["earliest_start_time"]),
            latest_end_time=datetime.fromisoformat(task_data["latest_end_time"]),
            visible_windows=visible_windows,
            task_type=task_data["task_type"],
            cluster_names=None
        )
        tasks.append(task)

    return tasks
def load_satellites(filename):
    """从JSON文件加载卫星数据并转换为Satellite对象"""
    with open(filename, 'r', encoding='utf-8') as f:
        satellites_data = json.load(f)

    satellites = []
    for sat_data in satellites_data:
        # 处理下行和充电时间窗口
        downlink_windows = []
        if 'downlink_windows' in sat_data:
            downlink_windows = [
                (datetime.fromisoformat(start), datetime.fromisoformat(end))
                for start, end in sat_data['downlink_windows']
            ]

        charging_windows = []
        if 'charging_windows' in sat_data:
            charging_windows = [
                (datetime.fromisoformat(start), datetime.fromisoformat(end))
                for start, end in sat_data['charging_windows']
            ]

        satellite = Satellite(
            sat_id=sat_data["sat_id"],
            tle_line1=sat_data["tle_line1"],
            tle_line2=sat_data["tle_line2"],
            sensor_type=sat_data["sensor_type"],
            resolution_capability=sat_data["resolution_capability"],
            battery_capacity=sat_data["battery_capacity"],
            data_storage=sat_data["data_storage"],
            imaging_speed=sat_data["imaging_speed"],
            downlink_windows=downlink_windows,
            charging_windows=charging_windows,
            cluster_names='cluster_1'
        )
        satellites.append(satellite)

    return satellites
def main():
    tasks = load_tasks("samples\\area\\tasks_data.json")
    satellites = load_satellites("samples\\area\\satellites_data.json")

    # 设置规划时间范围
    start_time = datetime(2023, 10, 1, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)
    completed_gravity=0.5
    balance_gravity=0.5
    priority_gravity=0.5
    # 创建简化调度器并运行
    scheduler = Scheduler(tasks, satellites, start_time, end_time,priority_gravity,balance_gravity,completed_gravity)
    scheduler.run()
    best_plan=scheduler.get_statistics('best')#综合最优方案
    best_task_plan=scheduler.get_statistics('task')#任务满足率最优方案
    best_resource_plan = scheduler.get_statistics('resource')#资源利用率最高方案
    best_quality_plan = scheduler.get_statistics('quality')#成像质量最优方案
    # 示例1: 获取并导出综合最优方案
    best_schedule =best_plan['schedule']#综合最佳方案
    scheduler.export_schedule(best_schedule, "综合最优", "output_plans")#保存
    best_plan_undownlinked_tasks_count=best_plan['undownlinked_tasks_count']#这个方案未下行卫星总数
    print(best_plan_undownlinked_tasks_count)
    best_plan_undownlinked_tasks=best_plan['undownlinked_tasks']#各卫星未下行任务
    for sat_id,stats in best_plan_undownlinked_tasks.items():
        print(f"卫星id:{sat_id},未下行任务:{stats}")

    best_completed_tasks=best_plan['completed_tasks']#完成调度的任务
    print(best_completed_tasks)
    best_entry_tasks=best_plan['entry_tasks']#受理的任务
    print(best_entry_tasks)
    best_plan_task_satisfaction=best_plan['task_satisfaction']#任务满足率
    print(best_plan_task_satisfaction)
    best_plan_task_resource_utilization=best_plan['resource_utilization']#任务满足率
    print(best_plan_task_resource_utilization)
    best_plan_task_imaging_quality=best_plan['imaging_quality']#任务满足率
    print(best_plan_task_imaging_quality)
if __name__ == '__main__':
    main()