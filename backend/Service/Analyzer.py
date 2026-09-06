from datetime import datetime
import time
from collections import defaultdict
from Service.task_scheduling import SatelliteScheduler


class ScheduleAnalyzer:
    """调度结果多维度分析器"""

    def __init__(self, schedule, tasks, satellites, algorithm_type="", start_time=None, end_time=None):
        """
        初始化分析器

        Args:
            schedule: 调度结果列表
            tasks: 所有任务列表
            satellites: 所有卫星列表
            algorithm_type: 使用的算法类型
            start_time: 规划周期开始时间
            end_time: 规划周期结束时间
        """
        self.schedule = schedule if schedule else []
        self.tasks = tasks
        self.satellites = satellites
        self.metrics = {}
        self.algorithm_type = algorithm_type
        self.planning_start_time = start_time
        self.planning_end_time = end_time
        self.cluster_cap = {}
        # 如果没有提供时间范围，尝试从调度结果中推断
        if not self.planning_start_time or not self.planning_end_time:
            self._infer_planning_period()

        # 预处理数据，提高后续分析效率
        self._preprocess_data()

    def _infer_planning_period(self):
        """从调度结果中推断规划周期"""
        if not self.schedule:
            return

        # 找出所有调度项中的最早开始时间和最晚结束时间
        start_times = [item['start_time'] for item in self.schedule if 'start_time' in item]
        end_times = [item['end_time'] for item in self.schedule if 'end_time' in item]

        if start_times:
            self.planning_start_time = min(start_times)
        if end_times:
            self.planning_end_time = max(end_times)

    def _preprocess_data(self):
        """预处理数据以提高分析效率"""
        # 创建任务ID到任务对象的映射
        self.task_map = {task.task_id: task for task in self.tasks}

        # 创建卫星ID到卫星对象的映射
        self.satellite_map = {sat.sat_id: sat for sat in self.satellites}

        # 创建已分配任务的集合
        self.assigned_task_ids = {item['task_id'] for item in self.schedule}

        # 按卫星ID分组的调度项
        self.satellite_schedules = {}
        for item in self.schedule:
            sat_id = item['satellite_id']
            if sat_id not in self.satellite_schedules:
                self.satellite_schedules[sat_id] = []
            self.satellite_schedules[sat_id].append(item)

    def analyze_all(self):
        """执行全部分析并返回结果"""
        self.analyze_task_satisfaction()
        self.analyze_satellite_utilization()
        self.analyze_imaging_quality()
        self.analyze_plan_summary()  # 添加新的总体概览分析
        return self.metrics

    def analyze_task_satisfaction(self):
        """分析任务满足率"""
        total_tasks = len(self.tasks)
        if total_tasks == 0:
            self.metrics['task_satisfaction'] = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'completion_rate': 0,
                'priority_completion': {},
                'weighted_completion_rate': 0
            }
            return

        # 获取已完成任务
        completed_tasks = len(self.assigned_task_ids)
        completion_rate = completed_tasks / total_tasks

        # 按优先级统计任务完成情况
        priority_counts = {}
        priority_completed = {}
        priority_weights = {}  # 每个优先级的权重

        # 初始化优先级计数
        for task in self.tasks:
            priority = task.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            priority_completed[priority] = 0
            # 优先级越高，权重越大
            priority_weights[priority] = priority ** 2  # 使用平方增加高优先级的权重差异

        # 统计已完成任务的优先级分布
        for task in self.tasks:
            if task.task_id in self.assigned_task_ids:
                priority_completed[task.priority] += 1

        # 计算加权完成率
        priority_rates = {}
        total_weight = 0
        weighted_sum = 0

        for priority, count in priority_counts.items():
            completed = priority_completed[priority]
            rate = completed / count if count > 0 else 0
            priority_rates[priority] = rate

            weight = priority_weights[priority] * count
            total_weight += weight
            weighted_sum += weight * rate

        weighted_completion_rate = weighted_sum / total_weight if total_weight > 0 else 0

        # 保存结果
        self.metrics['task_satisfaction'] = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_rate': completion_rate,
            'priority_completion': {
                priority: {
                    'total': count,
                    'completed': priority_completed[priority],
                    'rate': priority_rates[priority]
                } for priority, count in priority_counts.items()
            },
            'weighted_completion_rate': weighted_completion_rate,
        }

    def analyze_satellite_utilization(self):
        """分析卫星资源利用率"""
        if not self.satellites or not self.schedule:
            self.metrics['satellite_utilization'] = {
                'overall_utilization': 0,
                'satellite_details': {},
                'overall_undownlinked_count': 0
            }
            return
        overall_undownlinked_count = 0
        # 初始化每颗卫星的统计数据
        satellite_stats = {}
        for sat in self.satellites:
            satellite_stats[sat.sat_id] = {
                'sat_cluster_name': 0,
                'task_count': 0,
                'observation_time_seconds': 0,
                'maneuver_time_seconds': 0,
                'battery_usage_wh': 0,
                'final_battery_usage_wh': 0,
                'final_storage_usage_gb': 0,
                'storage_usage_gb': 0,
                'total_time_seconds': 0,
                'available_time_seconds': 0,  # 可用时间（时间窗口总和）
                'idle_time_seconds': 0,  # 新增：相邻任务之间的空闲时间
                'attitude_change_total': 0,  # 新增：姿态变化累计量
                'task_transitions': 0,  # 新增：任务转换次数
                'task_priority_sum': 0,  # 新增：已完成任务优先级总和
                'undownlinked_tasks': [],
                'undownlinked_tasks_count': 0,
                'battery_cap': sat.battery_capacity,
                'storage_cap': sat.data_storage
            }
            for cluster_name in sat.cluster_names:
                self.cluster_cap.setdefault(cluster_name, {'battery_cap': 0, 'storage_cap': 0})
                cluster_battery_cap = self.cluster_cap[cluster_name].get('battery_cap', 0) + sat.battery_capacity
                cluster_storage_cap = self.cluster_cap[cluster_name].get('storage_cap', 0) + sat.data_storage
                self.cluster_cap[cluster_name] = {'battery_cap': cluster_battery_cap,
                                                  'storage_cap': cluster_storage_cap

                                                  }

        # 统计每颗卫星的任务和资源使用
        for sat_id, items in self.satellite_schedules.items():
            if sat_id not in satellite_stats:
                continue
            satellite_stats[sat_id]['sat_cluster_name'] = items[0].get('sat_cluster_name')
            # 更新任务计数
            satellite_stats[sat_id]['task_count'] = len(items)
            # 按时间排序任务
            sorted_items = sorted(items, key=lambda x: x['start_time'])
            last_task = sorted_items[-1]
            last_battery = last_task['battery_after_task']
            sorted_items[-1]['battery_after_task'] = last_task['battery_after_task']
            # 累计已完成任务的优先级总和
            # 确保每个任务项有priority属性，如果没有则使用task对象的priority
            for item in sorted_items:
                priority = item.get('priority', 0)
                # 如果任务项没有直接的priority，尝试从task对象获取
                if priority == 0 and 'task_id' in item:
                    task = self.task_map.get(item['task_id'])
                    if task and hasattr(task, 'priority'):
                        priority = task.priority
                satellite_stats[sat_id]['task_priority_sum'] += priority
                satellite_stats[sat_id]['undownlinked_tasks'] = item.get('final_stored_tasks') or []
            satellite_stats[sat_id]['undownlinked_tasks_count'] = len(satellite_stats[sat_id]['undownlinked_tasks'])
            overall_undownlinked_count += satellite_stats[sat_id]['undownlinked_tasks_count']
            # 跟踪上一个任务的结束时间和姿态
            prev_end_time = None
            prev_attitude = None

            for i, item in enumerate(sorted_items):
                # 时间统计
                start_time = item['start_time']
                earliest_start_time = item['earliest_sat_start_time']
                end_time = item['end_time']
                duration_seconds = (end_time - start_time).total_seconds()
                satellite_stats[sat_id]['total_time_seconds'] += duration_seconds
                satellite_stats[sat_id]['final_storage_usage_gb'] = item.get('final_storage_with_downlink')
                satellite_stats[sat_id]['final_battery_usage_wh'] = satellite_stats[sat_id]['battery_cap'] - item.get(
                    'battery_after_task')
                last_task = sorted_items[-1]
                last_battery = satellite_stats[sat_id]['final_battery_usage_wh']
                final_battery = last_battery + 20 * (
                        self.planning_end_time - last_task['end_time']).total_seconds() / 3600
                satellite_stats[sat_id]['final_battery_usage_wh'] = final_battery
                if prev_end_time and start_time > prev_end_time:
                    idle_time = (start_time - prev_end_time).total_seconds()
                    interval_time = (earliest_start_time - prev_end_time).total_seconds()
                    idle_time = idle_time - interval_time
                    satellite_stats[sat_id]['idle_time_seconds'] += idle_time

                # 计算姿态变化量 - 修复NumPy数组布尔值判断问题
                current_attitude = item.get('attitude_after_task')
                if prev_attitude is not None and current_attitude is not None:
                    # 使用NumPy的norm计算姿态向量差的范数，或简单地计算各分量差的绝对值之和
                    import numpy as np
                    try:
                        # 如果是NumPy数组，计算向量差的范数
                        attitude_change = np.linalg.norm(np.array(current_attitude) - np.array(prev_attitude))
                    except Exception as e:
                        # 回退到简单的元素差异计算
                        print(f"姿态范数计算失败，回退到元素差异计算: {e}")
                        try:
                            attitude_change = sum(abs(a - b) for a, b in zip(prev_attitude, current_attitude))
                        except Exception as e2:
                            print(f"姿态变化计算失败，使用默认值0: {e2}")
                            attitude_change = 0  # 无法计算姿态变化时的默认值

                    satellite_stats[sat_id]['attitude_change_total'] += attitude_change
                    satellite_stats[sat_id]['task_transitions'] += 1
                # 更新前一任务信息
                prev_end_time = end_time
                prev_attitude = current_attitude

                # 观测和机动时间
                obs_seconds = item['observation_time']
                satellite_stats[sat_id]['observation_time_seconds'] += obs_seconds

                maneuver_seconds = item['maneuver_duration']
                satellite_stats[sat_id]['maneuver_time_seconds'] += maneuver_seconds

                # 电量使用
                if 'battery_before_task' in item and 'battery_after_task' in item:
                    battery_usage = item['battery_before_task'] - item['battery_after_task']
                    satellite_stats[sat_id]['battery_usage_wh'] += max(0, battery_usage)  # 确保不为负

                # 存储使用
                if 'storage_added' in item:
                    satellite_stats[sat_id]['storage_usage_gb'] += item['storage_added']

        # 计算每颗卫星的可用时间（从任务的时间窗口推断）
        for task in self.tasks:
            if hasattr(task, 'visible_windows') and task.visible_windows:
                for sat_id, windows in task.visible_windows.items():
                    if sat_id in satellite_stats:
                        for start, end in windows:
                            window_duration = (end - start).total_seconds()
                            satellite_stats[sat_id]['available_time_seconds'] += window_duration

        # 计算利用率
        overall_task_count = 0
        overall_priority_sum = 0
        overall_observation_time = 0
        overall_maneuver_time = 0
        overall_idle_time = 0
        overall_available_time = 0
        overall_battery_usage = 0
        overall_battery_capacity = 0
        overall_attitude_efficiency = 0
        overall_task_transitions = 0

        for sat_id, stats in satellite_stats.items():
            # 获取卫星对象
            satellite = self.satellite_map.get(sat_id)
            if not satellite:
                continue

            # 基本时间利用率
            available_time = stats['available_time_seconds']
            if available_time > 0:
                stats['time_utilization'] = stats['total_time_seconds'] / available_time
            else:
                stats['time_utilization'] = 0

            # 新增：任务密度 (越高越好)
            total_operational_time = stats['total_time_seconds'] + stats['idle_time_seconds']
            if total_operational_time > 0:
                stats['task_density'] = stats['total_time_seconds'] / total_operational_time
            else:
                stats['task_density'] = 0

            # 新增：观测时间比例 (观测时间/总任务时间，越高越好)
            if stats['total_time_seconds'] > 0:
                stats['observation_ratio'] = stats['observation_time_seconds'] / stats['total_time_seconds']
            else:
                stats['observation_ratio'] = 0

            # 新增：姿态效率 (避免除零错误)
            if stats['attitude_change_total'] > 0 and stats['task_transitions'] > 0:
                stats['attitude_efficiency'] = stats['task_count'] / (stats['attitude_change_total'] + 0.001)
            else:
                stats['attitude_efficiency'] = 1  # 如果没有姿态变化，则效率为最高

            # 新增：能源效率 (任务优先级总和/电池使用量，越高越好)
            if stats['battery_usage_wh'] > 0:
                stats['energy_efficiency'] = stats['task_priority_sum'] / stats['battery_usage_wh']
            else:
                stats['energy_efficiency'] = 0

            # 电池利用率
            stats['battery_capacity'] = satellite.battery_capacity
            stats['battery_utilization'] = stats[
                                               'battery_usage_wh'] / satellite.battery_capacity if satellite.battery_capacity > 0 else 0

            # 存储利用率
            stats['storage_capacity'] = satellite.data_storage
            stats['storage_utilization'] = stats[
                                               'storage_usage_gb'] / satellite.data_storage if satellite.data_storage > 0 else 0

            # 累加总量
            overall_task_count += stats['task_count']
            overall_priority_sum += stats['task_priority_sum']
            overall_observation_time += stats['observation_time_seconds']
            overall_maneuver_time += stats['maneuver_time_seconds']
            overall_idle_time += stats['idle_time_seconds']
            overall_available_time += available_time
            overall_battery_usage += stats['battery_usage_wh']
            overall_battery_capacity += satellite.battery_capacity
            if stats['attitude_change_total'] > 0:
                overall_attitude_efficiency += (stats['task_count'] / (stats['attitude_change_total'] + 0.001)) * stats[
                    'task_count']
            overall_task_transitions += stats['task_transitions']

        # 计算整体效率指标
        overall_task_density = 0
        overall_observation_ratio = 0
        overall_energy_efficiency = 0

        total_operational_time = sum(stats['total_time_seconds'] + stats['idle_time_seconds']
                                     for stats in satellite_stats.values())
        total_task_time = sum(stats['total_time_seconds'] for stats in satellite_stats.values())

        # 将total_task_time赋值给overall_task_time
        overall_task_time = total_task_time

        if total_operational_time > 0:
            overall_task_density = total_task_time / total_operational_time

        if total_task_time > 0:
            overall_observation_ratio = overall_observation_time / total_task_time

        if overall_battery_usage > 0:
            overall_energy_efficiency = overall_priority_sum / overall_battery_usage

        # 修正姿态效率计算，避免除零问题
        if overall_task_count > 0:
            overall_attitude_efficiency = overall_attitude_efficiency / max(1, overall_task_count)
        else:
            overall_attitude_efficiency = 1

        # 计算任务负载均衡度（标准差/平均值）
        task_counts = [stats['task_count'] for sat_id, stats in satellite_stats.items()]
        if task_counts:
            avg_tasks = sum(task_counts) / len(task_counts)
            task_std_dev = (sum((c - avg_tasks) ** 2 for c in task_counts) / len(task_counts)) ** 0.5
            load_balance = 1 / (1 + task_std_dev) if avg_tasks > 0 else 0  # 负载越均衡，该值越接近1
        else:
            load_balance = 0

        # 保存结果
        self.metrics['satellite_utilization'] = {
            'overall_utilization': {
                # 新指标 - 效率导向
                'task_density': overall_task_density,  # 任务密度：减少空闲时间
                'observation_ratio': overall_observation_ratio,  # 观测比例：有效观测时间比例
                'energy_efficiency': overall_energy_efficiency,  # 能源效率：单位能量完成任务价值
                'attitude_efficiency': overall_attitude_efficiency,  # 姿态效率：减少过度姿态调整
                'load_balance': load_balance,  # 负载均衡：任务分配均匀性
                'overall_undownlinked_count': overall_undownlinked_count,
                # 保留原指标作为参考
                'time_utilization': overall_task_time / overall_available_time if overall_available_time > 0 else 0,
                'battery_utilization': overall_battery_usage / overall_battery_capacity if overall_battery_capacity > 0 else 0,

                # 添加汇总指标
                'total_tasks': overall_task_count,
                'total_priority_sum': overall_priority_sum,
                'total_observation_time': overall_observation_time,
                'total_maneuver_time': overall_maneuver_time,
                'total_idle_time': overall_idle_time
            },
            'satellite_details': satellite_stats
        }

    def analyze_imaging_quality(self):
        """分析成像质量（分辨率和观测完成率）"""
        if not self.schedule:
            self.metrics['imaging_quality'] = {
                'average_resolution_ratio': 0,
                'resolution_distribution': {},
                'observation_completion_rate': 0,
                'detailed_stats': {}
            }
            return

        # 初始化统计数据
        total_area = 0
        weighted_resolution_sum = 0
        resolution_distribution = {}  # 不同分辨率区间的任务数量分布
        resolution_brackets = [0.5, 1, 2, 5, 10, float('inf')]  # 分辨率区间边界

        for bracket in resolution_brackets[:-1]:
            next_bracket = next((b for b in resolution_brackets if b > bracket), float('inf'))
            key = f"{bracket}-{next_bracket if next_bracket != float('inf') else '以上'}"
            resolution_distribution[key] = 0

        # 按任务统计详细信息
        task_stats = {}

        # 统计每个任务的成像质量
        for task_id in self.assigned_task_ids:
            task = self.task_map.get(task_id)
            if not task:
                continue

            # 获取任务的调度项
            schedule_items = [item for item in self.schedule if item['task_id'] == task_id]
            if not schedule_items:
                continue

            # 使用第一个调度项（通常一个任务只对应一个调度项）
            item = schedule_items[0]

            # 计算分辨率比率（任务要求分辨率/卫星能力）
            satellite = self.satellite_map.get(item['satellite_id'])
            if not satellite:
                continue

            # 任务未指定要求分辨率时按卫星能力计，避免 None 参与运算
            task_resolution = task.resolution if task.resolution else satellite.resolution_capability
            resolution_ratio = task_resolution / satellite.resolution_capability  # 值越小越好

            # 任务面积
            area = task.target_length * task.target_width
            total_area += area

            # 加权分辨率（按面积加权）
            weighted_resolution_sum += resolution_ratio * area

            # 更新分辨率分布
            for bracket in resolution_brackets[:-1]:
                next_bracket = next((b for b in resolution_brackets if b > bracket), float('inf'))
                if bracket <= satellite.resolution_capability < next_bracket:
                    key = f"{bracket}-{next_bracket if next_bracket != float('inf') else '以上'}"
                    resolution_distribution[key] += 1
                    break

            # 计算观测完成率
            # 观测完成率 = 实际观测时间 / 理想观测时间
            actual_observation_time = item['observation_time'].total_seconds() if hasattr(item['observation_time'],
                                                                                          'total_seconds') else 0

            # 计算理想观测时间（基于任务属性和卫星性能）
            ideal_observation_time = satellite.get_observation_time(task,
                                                                    item['start_time']).total_seconds() if hasattr(
                satellite.get_observation_time(task, item['start_time']), 'total_seconds') else 1

            observation_completion = actual_observation_time / ideal_observation_time if ideal_observation_time > 0 else 0

            # 保存任务统计信息
            task_stats[task_id] = {
                'resolution_required': task.resolution,
                'resolution_provided': satellite.resolution_capability,
                'resolution_ratio': resolution_ratio,
                'actual_observation_time': actual_observation_time,
                'ideal_observation_time': ideal_observation_time,
                'observation_completion_rate': observation_completion,
                'area': area
            }

        # 计算平均分辨率比率（按面积加权）
        avg_resolution_ratio = weighted_resolution_sum / total_area if total_area > 0 else 0

        # 计算整体观测完成率
        total_actual_time = sum(stats['actual_observation_time'] for stats in task_stats.values())
        total_ideal_time = sum(stats['ideal_observation_time'] for stats in task_stats.values())
        overall_completion_rate = total_actual_time / total_ideal_time if total_ideal_time > 0 else 0

        # 保存结果
        self.metrics['imaging_quality'] = {
            'average_resolution_ratio': avg_resolution_ratio,
            'resolution_distribution': resolution_distribution,
            'observation_completion_rate': overall_completion_rate,
            'detailed_stats': task_stats
        }

    def analyze_plan_summary(self):
        """分析规划总体概览指标"""
        if not self.schedule:
            self.metrics['plan_summary'] = {
                'total_schedule_items': 0,
                'time_span_seconds': 0,
                'satellites_used': 0,
                'avg_tasks_per_satellite': 0
            }
            return

        # 计算总调度项数量
        total_items = len(self.schedule)

        # 计算规划时间跨度
        if self.planning_start_time and self.planning_end_time:
            time_span = (self.planning_end_time - self.planning_start_time).total_seconds()
        else:
            time_span = 0

        # 计算使用的卫星数量
        satellites_used = len(self.satellite_schedules)

        # 计算每颗卫星平均任务数
        if satellites_used > 0:
            avg_tasks_per_satellite = total_items / satellites_used
        else:
            avg_tasks_per_satellite = 0

        # 保存结果
        self.metrics['plan_summary'] = {
            'total_schedule_items': total_items,
            'time_span_seconds': time_span,
            'satellites_used': satellites_used,
            'avg_tasks_per_satellite': avg_tasks_per_satellite
        }

    def get_comprehensive_score(self):
        """计算综合评分(0-100)"""
        if not self.metrics:
            self.analyze_all()

        score = 0
        total_weight = 0

        # 任务满足率评分 (权重 40)
        if 'task_satisfaction' in self.metrics:
            ts = self.metrics['task_satisfaction']
            # 基础任务完成率
            completion_score = ts['completion_rate'] * 80
            # 加权任务完成率（考虑优先级）
            weighted_score = ts['weighted_completion_rate'] * 20
            score += 40 * (completion_score + weighted_score) / 100
            total_weight += 40

        # 卫星利用率评分 (权重 30) - 使用新指标
        if 'satellite_utilization' in self.metrics:
            su = self.metrics['satellite_utilization']['overall_utilization']

            # 任务密度 (25分) - 减少空闲时间
            density_score = min(su.get('task_density', 0), 0.95) / 0.95 * 25  # 95%获得满分

            # 观测比例 (25分) - 有效观测时间比例
            observation_score = min(su.get('observation_ratio', 0), 0.8) / 0.8 * 25  # 80%获得满分

            # 能源效率 (25分) - 单位能量完成的任务价值
            # 需要归一化能源效率，以5作为基准比率（每单位能量完成优先级总和5）
            energy_score = min(su.get('energy_efficiency', 0), 5) / 5 * 25

            # 负载均衡性 (25分)
            balance_score = su.get('load_balance', 0) * 25

            # 综合卫星利用率分数
            score += 30 * (density_score + observation_score + energy_score + balance_score) / 100
            total_weight += 30

        # 成像质量评分 (权重 30)
        if 'imaging_quality' in self.metrics:
            iq = self.metrics['imaging_quality']
            # 分辨率评分 (越小越好，假设1.0是理想值)
            resolution_score = min(1.0, 1.0 / max(0.1, iq['average_resolution_ratio'])) * 50
            # 观测完成率
            completion_score = iq['observation_completion_rate'] * 50
            score += 30 * (resolution_score + completion_score) / 100
            total_weight += 30

        # 归一化得分
        if total_weight > 0:
            final_score = score / total_weight * 100
        else:
            final_score = 0

        return round(final_score, 2)


class PlanComparator:
    """卫星任务规划方案比选器"""

    def __init__(self, tasks, satellites, start_time, end_time, priority_gravity=3.0, balance_gravity=0.3,
                 completed_gravity=0.5):
        """
        初始化比选器

        Args:
            tasks: 任务列表
            satellites: 卫星列表
            start_time: 规划开始时间
            end_time: 规划结束时间
        """
        self.cluster_cap = {}
        self.tasks = tasks
        self.satellites = satellites
        self.start_time = start_time
        self.end_time = end_time
        self.plans = []
        self.best_plans = {}  # 存储不同指标的最优方案
        self.priority_gravity = priority_gravity
        self.balance_gravity = balance_gravity
        self.completed_gravity = completed_gravity

    def add_strategy(self, name, algorithm, **params):
        """
        添加规划策略

        Args:
            name: 策略名称
            algorithm: 算法类型
            **params: 算法参数
        """
        self.strategies = getattr(self, 'strategies', [])
        self.strategies.append({
            "name": name,
            "algorithm": algorithm,
            "params": params
        })

    def run_comparison(self):
        """运行所有策略并比较结果"""
        if not hasattr(self, 'strategies') or not self.strategies:
            raise ValueError("请先添加规划策略")

        print("正在生成多个规划方案...")

        # 清空之前的结果
        self.plans = []

        # 为每种策略生成调度计划
        for strategy in self.strategies:
            print(f"\n正在使用 {strategy['name']} 规划...")

            # 创建调度器
            print(self.end_time)
            scheduler = SatelliteScheduler(
                self.tasks,
                self.satellites,
                self.start_time,
                self.end_time,
                strategy["algorithm"],
                self.priority_gravity, self.balance_gravity, self.completed_gravity
            )

            # 设置算法参数
            for param_name, param_value in strategy.get('params', {}).items():
                if hasattr(scheduler, param_name):
                    setattr(scheduler, param_name, param_value)

            # 记录开始时间
            start_time_alg = time.time()

            # 解决调度问题
            schedule1 = scheduler.solve()
            # print(f"analyzer{strategy["name"]}调度结果为{schedule1}")
            # 计算执行时间
            execution_time_seconds = time.time() - start_time_alg

            # 分析方案
            analyzer = ScheduleAnalyzer(
                schedule1,
                self.tasks,
                self.satellites,
                algorithm_type=strategy["name"],
                start_time=self.start_time,
                end_time=self.end_time
            )
            # print(f"分析完{strategy["name"]}调度结果为{schedule1}")
            # 执行全部分析
            analyzer.analyze_all()
            self.cluster_cap = analyzer.cluster_cap
            # 获取综合评分
            if analyzer.schedule:
                score = analyzer.get_comprehensive_score()
            else:
                return

            # 提取三个核心指标
            # 1. 任务满足率指标
            task_satisfaction = analyzer.metrics['task_satisfaction']['weighted_completion_rate'] \
                if 'task_satisfaction' in analyzer.metrics else 0

            # 2. 资源利用率指标 - 综合新的指标体系
            # 2. 资源利用率指标 - 综合新的指标体系
            sat_metrics = analyzer.metrics.get('satellite_utilization', {}).get('overall_utilization', {})

            # 获取各项利用率指标
            time_util = sat_metrics.get('time_utilization', 0)
            task_density = sat_metrics.get('task_density', 0)
            energy_efficiency = sat_metrics.get('energy_efficiency', 0)
            battery_utilization = sat_metrics.get('battery_utilization', 0)
            load_balance = sat_metrics.get('load_balance', 0)

            # 计算综合资源利用率指标 (按照任务书要求计算)
            # 主要考虑时间利用率(70%)和能源利用率(30%)
            # resource_utilization = (0.7 * time_util +
            #                         0.3 * battery_utilization)
            resource_utilization = task_density
            # 3. 成像质量指标
            imaging_quality = analyzer.metrics['imaging_quality']['observation_completion_rate'] \
                if 'imaging_quality' in analyzer.metrics else 0
            # 保存方案信息
            undowlinked_tasks_count = sat_metrics.get('overall_undownlinked_count')
            sat_storage_tasks = {}
            cluster_status = defaultdict(lambda: {
                'cluster_storage_cost': 0,
                'cluster_battery_cost': 0,
                'cluster_time_cost': 0,
                'cluster_utilization': 0,
                'cluster_tasks_count': 0,
                'cluster_storage_cap': 0,
                'cluster_battery_cap': 0
            })
            overall_storage_cost = 0
            overall_battery_cost = 0
            sat_stats = analyzer.metrics.get('satellite_utilization', {}).get('satellite_details', {})
            for sat_id, stats in sat_stats.items():
                # print(stats)
                sat_storage_tasks[sat_id] = stats.get('undownlinked_tasks', [])
                overall_battery_cost += stats.get('final_battery_usage_wh', 0)
                overall_storage_cost += stats.get('final_storage_usage_gb', 0)
                cluster_names = stats.get('sat_cluster_name', '')
                if not cluster_names:
                    continue
                for cluster_name in cluster_names:
                    if cluster_name:
                        # 检查键是否存在，不存在则初始化
                        if cluster_name not in cluster_status:
                            cluster_status[cluster_name] = {
                                'cluster_storage_cost': 0,
                                'cluster_battery_cost': 0,
                                'cluster_storage_cap': 0,
                                'cluster_battery_cap': 0,
                                'cluster_time_cost': 0,
                                'cluster_utilization': 0,
                                'cluster_tasks_count': 0
                            }

                    cluster_before_storage = cluster_status[cluster_name].get('cluster_storage_cost') or 0
                    cluster_before_battery = cluster_status[cluster_name].get('cluster_battery_cost') or 0
                    cluster_tasks_count = cluster_status[cluster_name].get('cluster_tasks_count', 0)
                    cluster_tasks_count += stats.get('task_count', 0)
                    status_storage_cap = stats.get('storage_cap', 0)
                    status_battery_cap = stats.get('battery_cap', 0)
                    cluster_storage_cap = self.cluster_cap[cluster_name].get('storage_cap', 0)
                    cluster_battery_cap = self.cluster_cap[cluster_name].get('battery_cap', 0)
                    cluster_after_storage = cluster_before_storage + stats.get('final_storage_usage_gb', 0)
                    cluster_after_battery = cluster_before_battery + stats.get('final_battery_usage_wh', 0)
                    print(f"卫星{sat_id}消耗存储{stats.get('final_storage_usage_gb', 0)}")
                    cluster_before_time = cluster_status[cluster_name].get('cluster_time_cost') or 0
                    # 除零保护：容量为0时利用率置0，跳过除法
                    battery_utilization = cluster_after_battery / cluster_battery_cap if cluster_battery_cap else 0
                    storage_utilization = cluster_after_storage / cluster_storage_cap if cluster_storage_cap else 0
                    cluster_after_time = cluster_before_time + stats.get('observation_time_seconds', 0) + stats.get(
                        'maneuver_time_seconds', 0)
                    # print(f"卫星{sat_id}观测时间{stats.get('observation_time_seconds', 0)}")
                    cluster_status[cluster_name] = {
                        'cluster_storage_cost': cluster_after_storage,
                        'cluster_battery_cost': cluster_after_battery,
                        'cluster_storage_cap': cluster_storage_cap,
                        'cluster_battery_cap': cluster_battery_cap,
                        'cluster_time_cost': cluster_after_time,
                        'cluster_tasks_count': cluster_tasks_count,
                        'cluster_battery_utilization': battery_utilization,
                        'cluster_storage_utilization': storage_utilization,
                    }
            plan = {
                "name": strategy["name"],
                "algorithm": strategy["algorithm"],
                "params": strategy.get('params', {}),
                "schedule": schedule1,
                "overall_storage_cost": overall_storage_cost,
                "overall_battery_cost": overall_battery_cost,
                "scheduler": scheduler,  # 保存调度器以便后续使用
                "execution_time": execution_time_seconds,
                "analyzer": analyzer,
                "score": score,
                "cluster_status": cluster_status,
                "undownlinked_tasks_count": undowlinked_tasks_count,
                "undownlinked_tasks": sat_storage_tasks,
                "completed_tasks": len(schedule1),  # 已分配任务数
                "entry_tasks": len(self.tasks),  # 受理任务数
                "task_satisfaction": task_satisfaction,
                "resource_utilization": resource_utilization,  # 综合资源利用率
                "imaging_quality": imaging_quality,
            }
            # print(f"plan中{strategy["name"]}schedule为{schedule1}")
            self.plans.append(plan)

            print(
                f"  完成！调度了 {len(schedule1)}/{len(self.tasks)} 个任务，耗时 {execution_time_seconds:.2f} 秒，综合评分: {score:.2f}")

        # 找出不同指标的最优方案
        self.identify_best_plans()

        return self.plans

    def identify_best_plans(self):
        """找出不同指标的最优方案"""
        if not self.plans:
            return

        # 综合得分最高的方案
        self.best_plans['overall'] = max(self.plans, key=lambda x: x["score"])

        # 任务满足率最高的方案
        self.best_plans['task_satisfaction'] = max(self.plans, key=lambda x: x["task_satisfaction"])

        # 资源利用率最高的方案 (使用综合资源利用率)
        self.best_plans['resource_utilization'] = max(self.plans, key=lambda x: x["resource_utilization"])

        # 成像质量最高的方案
        self.best_plans['imaging_quality'] = max(self.plans, key=lambda x: x["imaging_quality"])


class SimplifiedSatelliteScheduler:
    """卫星任务调度器 - 超简化API"""

    def __init__(self, tasks, satellites, start_time, end_time, priority_gravity=3.0, balance_gravity=0.3,
                 completed_gravity=0.5):
        """
        初始化调度器

        Args:
            tasks: 任务列表
            satellites: 卫星列表
            start_time: 规划开始时间
            end_time: 规划结束时间
        """
        self.tasks = tasks
        self.satellites = satellites
        self.start_time = start_time
        self.end_time = end_time
        self.best_plans = {}  # 存储四种最优方案
        self._comparator = None  # 内部比选器
        self.priority_gravity = priority_gravity
        self.balance_gravity = balance_gravity
        self.completed_gravity = completed_gravity
        self.algorithm_metrics = {}

    def run(self):
        """
        运行调度优化，自动使用三种算法并找出四种最优方案

        Returns:
            self，便于链式调用
        """
        # 创建方案比选器
        self._comparator = PlanComparator(self.tasks, self.satellites, self.start_time, self.end_time,
                                          self.priority_gravity, self.balance_gravity, self.completed_gravity)

        # 默认添加三种算法
        self._comparator.add_strategy("遗传算法", "genetic", )
        self._comparator.add_strategy("贪心算法", "greedy")
        self._comparator.add_strategy("蚁群算法", "ant_colony")

        # 运行比较
        self._comparator.run_comparison()
        plans = self._comparator.plans
        print(f"plans中{plans}")
        if len(plans) == 0:
            return
        # 按算法分组提取指标
        self.algorithm_metrics = {}

        for plan in plans:
            algorithm = plan["algorithm"]
            # 每次都覆盖之前的指标
            self.algorithm_metrics[algorithm] = {
                "task_satisfaction": plan["task_satisfaction"],
                "resource_utilization": plan["resource_utilization"],
                "imaging_quality": plan["imaging_quality"],
                "schedule": plan["schedule"],
                'overall_storage_cost': plan['overall_storage_cost'],  # 所有星簇卫星总存储消耗gb
                'overall_battery_cost': plan['overall_battery_cost']  # 所有星簇卫星电量消耗wh
            }

        # 提取最优方案
        self.best_plans = {
            'best': self._comparator.best_plans['overall'],
            'task': self._comparator.best_plans['task_satisfaction'],
            'resource': self._comparator.best_plans['resource_utilization'],
            'quality': self._comparator.best_plans['imaging_quality']
        }

        # 打印简要结果
        print("规划已完成，已找到以下最优方案：")
        print(f"- 综合最优方案: {self.best_plans['best']['name']}, 评分: {self.best_plans['best']['score']:.2f}")
        print(
            f"- 任务满足率最高方案: {self.best_plans['task']['name']}, 满足率: {self.best_plans['task']['task_satisfaction']:.2%}")
        print(
            f"- 资源利用率最高方案: {self.best_plans['resource']['name']}, 利用率: {self.best_plans['resource']['resource_utilization']:.2%}")
        print(
            f"- 成像质量最高方案: {self.best_plans['quality']['name']}, 质量指标: {self.best_plans['quality']['imaging_quality']:.2%}")

        return self

    def get_best_schedule(self, plan_type='best'):
        """
        获取指定最优方案的调度结果
        Args:
            plan_type: 方案类型，可选值:
                      'best' (综合最优),
                      'task' (任务满足率最优),
                      'resource' (资源利用率最优),
                      'quality' (成像质量最优)

        Returns:
            调度结果列表
        """
        if not self.best_plans:
            raise ValueError("请先调用run()方法")

        if plan_type not in self.best_plans:
            raise ValueError(f"未知的方案类型: {plan_type}，可选值: best, task, resource, quality")

        return self.best_plans[plan_type]['schedule']

    def get_algorithm_info(self, plan_type='best'):
        """
        获取指定方案的算法信息

        Args:
            plan_type: 方案类型，同上

        Returns:
            算法名称
        """
        if not self.best_plans:
            raise ValueError("请先调用run()方法")

        if plan_type not in self.best_plans:
            raise ValueError(f"未知的方案类型: {plan_type}")

        return self.best_plans[plan_type]['name']

    def get_statistics(self, plan_type='best'):
        """
        获取指定方案的算法信息

        Args:
            plan_type: 方案类型，同上

        Returns:
            算法名称
        """
        if not self.best_plans:
            raise ValueError("请先调用run()方法")

        if plan_type not in self.best_plans:
            raise ValueError(f"未知的方案类型: {plan_type}")
        statics = {
            'algorithm': self.best_plans[plan_type]['algorithm'],
            'schedule': self.best_plans[plan_type]['schedule'],  # 方案,字典
            'undownlinked_tasks_count': self.best_plans[plan_type]['undownlinked_tasks_count'],  # 仿真时间结束后未下行任务总量,数值
            'undownlinked_tasks': self.best_plans[plan_type]['undownlinked_tasks'],  # 各卫星未能下行任务：sat_id为索引的字典
            'completed_tasks': self.best_plans[plan_type]['completed_tasks'],  # 已分配任务数,数值
            'entry_tasks': self.best_plans[plan_type]['entry_tasks'],  # 受理任务数，数值
            'task_satisfaction': self.best_plans[plan_type]['task_satisfaction'],  # 任务满足率，数值
            'resource_utilization': self.best_plans[plan_type]['resource_utilization'],  # 资源利用率，数值
            'imaging_quality': self.best_plans[plan_type]['imaging_quality'],  # 成像质量，数值
            'overall_storage_cost': self.best_plans[plan_type]['overall_storage_cost'],
            'overall_battery_cost': self.best_plans[plan_type]['overall_battery_cost'],
            'cluster_status': self.best_plans[plan_type]['cluster_status']
        }
        return statics

    def merge_schedule(self, schedule):
        matching_scheduler = None

        # 首先检查是否为某个最优方案的schedule
        for plan_type, plan in self.best_plans.items():
            if schedule is plan['schedule']:  # 判断是否为同一个对象
                matching_scheduler = plan['scheduler']
                break

        # 如果找不到匹配的scheduler，使用第一个方案的scheduler
        if matching_scheduler is None and self.best_plans:
            matching_scheduler = next(iter(self.best_plans.values()))['scheduler']

        # 使用找到的scheduler保存Excel
        if matching_scheduler:

            res = matching_scheduler.merge_subtasks(schedule)
        else:
            raise ValueError("无法找到有效的scheduler来保存Excel")
        return res

    def export_schedule(self, schedule, algorithm_name=None, output_dir=None):
        """
        导出指定的调度结果到文件

        Args:
            schedule: 调度结果列表
            algorithm_name: 算法名称（可选）
            output_dir: 输出目录，默认为当前目录

        Returns:
            导出文件路径
        """
        if not schedule:
            raise ValueError("调度结果不能为空")

        # 确定输出目录
        if output_dir is None:
            output_dir = "."

        # 确保输出目录存在
        import os
        os.makedirs(output_dir, exist_ok=True)

        # 构建输出文件名
        algorithm_suffix = f"{algorithm_name}" if algorithm_name else ""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = os.path.join(output_dir, f"{algorithm_suffix}.xlsx")
        excel_path1 = os.path.join(output_dir, f"{algorithm_suffix}未合并.xlsx")
        txt_path = os.path.join(output_dir, f"{algorithm_suffix}.txt")
        txt_path1 = os.path.join(output_dir, f"{algorithm_suffix}未合并.txt")
        # 从最优方案中查找该schedule对应的scheduler
        matching_scheduler = None

        # 首先检查是否为某个最优方案的schedule
        for plan_type, plan in self.best_plans.items():
            if schedule is plan['schedule']:  # 判断是否为同一个对象
                matching_scheduler = plan['scheduler']
                break

        # 如果找不到匹配的scheduler，使用第一个方案的scheduler
        if matching_scheduler is None and self.best_plans:
            matching_scheduler = next(iter(self.best_plans.values()))['scheduler']

        # 使用找到的scheduler保存Excel
        if matching_scheduler:

            matching_scheduler.save_to_excel(schedule, excel_path, txt_path)
        else:
            raise ValueError("无法找到有效的scheduler来保存Excel")
        return excel_path
