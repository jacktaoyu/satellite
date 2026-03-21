from datetime import timedelta
import numpy as np
import time
from multiprocessing import Pool, cpu_count


class AntColonyOptimizer:
    """使用蚁群算法进行任务调度的优化器"""

    def __init__(self, tasks, sat_clusters, simulation_start_time=None, simulation_end_time=None,
                 priority_gravity=3.0, balance_gravity=0.3, completed_gravity=0.5):
        """
        初始化蚁群算法优化器

        Args:
            tasks: 任务列表
            sat_clusters: 卫星集群列表
            simulation_start_time: 仿真开始时间（可选）
            simulation_end_time: 仿真结束时间（可选）
        """
        self.tasks = tasks
        self.sat_clusters = sat_clusters
        self.simulation_start_time = simulation_start_time
        self.simulation_end_time = simulation_end_time
        self.priority_gravity = priority_gravity
        self.balance_gravity = balance_gravity
        self.completed_gravity = completed_gravity

        # 收集所有卫星
        self.satellites = []
        for cluster in self.sat_clusters:
            self.satellites.extend(cluster.get_satellites())

        # 任务-卫星可行性矩阵（记录哪些卫星可以执行哪些任务）
        self.task_satellite_feasibility = self._build_task_satellite_feasibility()

        # 初始化随机生成器
        self.random = np.random.RandomState()

        # 保存最佳调度结果
        self.best_schedule = []

        # 缓存卫星初始状态
        self._cache_satellite_initial_states()

        # 任务冲突检测缓存
        self.conflict_cache = {}

        # 初始化信息素矩阵
        self.pheromone = self._initialize_pheromone()

    def _initialize_pheromone(self):
        """初始化信息素矩阵"""
        pheromone = {}

        # 对每个任务，为所有可行的卫星选项初始化信息素
        for task_id, options in self.task_satellite_feasibility.items():
            pheromone[task_id] = {}
            for i, option in enumerate(options):
                satellite = option['satellite']
                pheromone[task_id][satellite.sat_id] = 1.0  # 初始信息素值

        return pheromone

    def _cache_satellite_initial_states(self):
        """缓存卫星的初始状态，用于快速重置"""
        self.original_satellite_states = {}

        for satellite in self.satellites:
            # 确保卫星状态是全新的
            satellite.reset_state()

            # 保存初始状态，确保使用字典结构
            initial_time = self.simulation_start_time
            initial_state = satellite.get_state_at(initial_time)
            self.original_satellite_states[satellite.sat_id] = {
                'timeline': {initial_time: initial_state} if hasattr(satellite, 'state_timeline') else {},
                'battery_level': initial_state['battery_level'],
                'current_storage': initial_state['current_storage'],
                'attitude': initial_state['attitude'].tolist()
            }

    def update_satellite_data_storage_with_downlink(self, schedule):
        """
        按照时间线更新卫星数据存储状态，考虑数据下行窗口

        使用schedule中的current_storage字段作为任务执行后的存储状态
        按照任务完成顺序处理，在上一个任务结束到当前任务结束期间计算可下行数据
        跟踪卫星上存储的任务数据，并在下行后从存储中移除

        Args:
            schedule: 最终的任务调度方案，包含current_storage字段

        Returns:
            更新后的调度方案（增加了下行后的存储状态和存储任务列表）
        """
        # 重置所有卫星到初始状态
        self._fast_reset_satellites()

        # 按卫星分组并按任务完成时间排序
        satellite_tasks = {}
        for sat in self.satellites:
            satellite_tasks[sat.sat_id] = []

        # 收集所有任务信息并排序
        for assignment in schedule:
            sat_id = assignment['satellite_id']
            if sat_id in satellite_tasks:
                task_id = assignment['task_id']
                task = next((t for t in self.tasks if t.task_id == task_id), None)
                print(f"蚁群算法中的观察时间为:{assignment.get('observation_time', 0)}")
                observation_value = assignment.get('observation_time', 0)
                observation_time = observation_value.total_seconds() if isinstance(observation_value,
                                                                                   timedelta) else observation_value

                if task:
                    satellite_tasks[sat_id].append({
                        'task': task,
                        'start_time': assignment['start_time'],
                        'end_time': assignment['end_time'],
                        'observation_time': observation_time,
                        'current_storage': assignment.get('current_storage', 0),
                        'assignment': assignment,
                        'storage_added': assignment.get('storage_added', 0)
                    })

        # 按任务完成时间排序
        for sat_id in satellite_tasks:
            satellite_tasks[sat_id].sort(key=lambda x: x['end_time'])

        # 为每个卫星处理任务和下行
        for sat_id, tasks in satellite_tasks.items():
            if not tasks:
                continue

            satellite = next((sat for sat in self.satellites if sat.sat_id == sat_id), None)
            if not satellite:
                continue

            print(f"\n调试信息 - 卫星{sat_id}下行处理:")

            # 初始化卫星状态
            satellite_storage = 0.0  # 卫星当前总存储量
            stored_tasks = []  # 卫星上存储的任务ID列表
            stored_task_data = {}  # 每个任务的数据量 {task_id: data_volume}
            last_task_end_time = None
            last_satellite_storage = 0.0
            last_stored_tasks = []

            # 处理每个任务
            for i, task_info in enumerate(tasks):
                task = task_info['task']
                task_id = task.task_id
                task_data = task_info['storage_added']  # 使用提供的存储增量
                start_time = task_info['start_time']
                end_time = task_info['end_time']

                # 使用schedule中提供的存储状态
                current_storage = task_info['current_storage']

                # 如果是第一个任务，初始化卫星存储状态
                if i == 0:
                    # 第一个任务前的存储量应该是零或者预设值
                    satellite_storage = current_storage - task_data

                # 将任务数据添加到卫星存储
                satellite_storage += task_data
                stored_tasks.append(task_id)
                stored_task_data[task_id] = task_data

                # 如果有上一个任务，检查在上一个任务结束到当前任务结束期间的下行情况
                if last_task_end_time:
                    print(f"  检查下行窗口: {last_task_end_time} 到 {end_time}")
                    print(f"  当前存储量: {last_satellite_storage:.2f}GB")
                    print(f"  存储的任务: {last_stored_tasks}")

                    # 处理在上一个任务结束到当前任务结束期间的下行
                    downlinked_data, downlinked_tasks = self._process_downlink_between_tasks_with_tasks(
                        satellite, last_task_end_time, end_time, last_satellite_storage, last_stored_tasks,
                        stored_task_data)

                    print(f"  下行数据量: {downlinked_data:.2f}GB, 下行任务: {downlinked_tasks}")

                    # 更新存储量和存储的任务
                    if downlinked_data > 0:
                        # 更新存储量
                        satellite_storage -= downlinked_data
                        if satellite_storage < 0:
                            satellite_storage = 0

                        # 从存储的任务列表中移除已下行的任务
                        for down_task_id in downlinked_tasks:
                            if down_task_id in stored_tasks:
                                stored_tasks.remove(down_task_id)
                                stored_task_data.pop(down_task_id, None)

                        print(f"  下行后剩余存储量: {satellite_storage:.2f}GB, 剩余任务: {stored_tasks}")

                    # 记录任务完成后的状态
                    task_info['assignment']['storage_after_task'] = satellite_storage
                    task_info['assignment']['stored_tasks_after_task'] = stored_tasks.copy()
                else:
                    # 第一个任务，没有前序下行
                    task_info['assignment']['storage_after_task'] = satellite_storage
                    task_info['assignment']['stored_tasks_after_task'] = stored_tasks.copy()

                # 更新最后任务完成时间
                last_task_end_time = end_time
                last_stored_tasks = stored_tasks.copy()
                last_satellite_storage = satellite_storage

            # 处理最后一个任务结束到仿真结束期间的下行
            if last_task_end_time and stored_tasks:
                simulation_end = self.simulation_end_time or (last_task_end_time + timedelta(days=1))
                print(f"  检查最终下行窗口: {last_task_end_time} 到 {simulation_end}")
                print(f"  最终存储量: {satellite_storage:.2f}GB")
                print(f"  最终存储的任务: {stored_tasks}")

                downlinked_data, downlinked_tasks = self._process_downlink_between_tasks_with_tasks(
                    satellite, last_task_end_time, last_task_end_time, satellite_storage, stored_tasks, stored_task_data)

                print(f"  最终下行数据量: {downlinked_data:.2f}GB, 下行任务: {downlinked_tasks}")

                # 更新最终存储状态
                final_storage = satellite_storage - downlinked_data
                if final_storage < 0:
                    final_storage = 0

                # 从存储的任务列表中移除已下行的任务
                final_stored_tasks = stored_tasks.copy()
                for task_id in downlinked_tasks:
                    if task_id in final_stored_tasks:
                        final_stored_tasks.remove(task_id)

                print(f"  仿真结束时最终存储量: {final_storage:.2f}GB, 最终存储任务: {final_stored_tasks}")

                # 记录每个任务的最终存储状态和存储的任务
                for task_info in tasks:
                    task_info['assignment']['final_storage_with_downlink'] = min(final_storage,satellite.data_storage)
                    task_info['assignment']['final_stored_tasks'] = final_stored_tasks.copy()

        # 更新并返回调度方案
        updated_schedule = [task_info['assignment'] for sat_tasks in satellite_tasks.values() for task_info in
                            sat_tasks]

        # 打印统计信息
        print("\n下行后的卫星存储状态统计:")
        for satellite in self.satellites:
            sat_tasks = [a for a in updated_schedule if a['satellite_id'] == satellite.sat_id]
            if sat_tasks:
                sat_tasks.sort(key=lambda x: x['end_time'])
                initial_storage = sat_tasks[-1].get('storage_after_task', 0)
                final_storage = sat_tasks[-1].get('final_storage_with_downlink', initial_storage)
                final_stored_tasks = sat_tasks[-1].get('final_stored_tasks', [])
                total_tasks = len(sat_tasks)
                downlinked = initial_storage - final_storage

                print(f"卫星{satellite.sat_id}: 执行了{total_tasks}个任务，"
                      f"任务后存储量{initial_storage:.2f}GB，"
                      f"下行数据量{downlinked:.2f}GB，"
                      f"下行后最终存储量{final_storage:.2f}GB")
                print(f"  最终存储的任务: {final_stored_tasks}")

        return updated_schedule

    def _process_downlink_between_tasks_with_tasks(self, satellite, start_time, end_time, available_storage,
                                                   stored_tasks, stored_task_data):
        """
        处理两个任务完成时间点之间的下行，同时跟踪下行的任务数据

        Args:
            satellite: 卫星对象
            start_time: 开始时间（上一个任务结束时间）
            end_time: 结束时间（当前任务结束时间）
            available_storage: 可下行的数据量(GB)
            stored_tasks: 卫星上存储的任务ID列表
            stored_task_data: 每个任务的数据量字典 {task_id: data_volume}

        Returns:
            tuple: (下行的数据量(GB), 下行的任务ID列表)
        """
        total_downlinked = 0.0
        downlinked_tasks = []
        sat_id = satellite.sat_id

        # 如果没有可下行数据或存储的任务，直接返回
        if available_storage <= 0 or not stored_tasks:
            print(f"  没有数据可下行: 存储量{available_storage:.2f}GB, 任务数{len(stored_tasks)}")
            return 0.0, []

        # 打印调试信息
        print(
            f"  处理下行时间段: {start_time} 到 {end_time}, 持续时间: {(end_time - start_time).total_seconds():.2f}秒")
        print(f"  可下行数据量: {available_storage:.2f}GB，存储任务数: {len(stored_tasks)}")

        # 检查卫星是否有下行窗口
        if not hasattr(satellite, 'downlink_windows') or not satellite.downlink_windows:
            print(f"  警告: 卫星{sat_id}没有下行窗口配置!")
            return 0.0, []

        print(f"  该卫星有{len(satellite.downlink_windows)}个下行窗口")

        # 获取下行速率 (Mbps)
        if not hasattr(satellite, 'downlink_rate') or satellite.downlink_rate <= 0:
            print(f"  警告: 卫星{sat_id}下行速率未设置或为零!")
            return 0.0, []

        downlink_rate = satellite.downlink_rate  # Mbps
        print(f"  下行速率: {downlink_rate} Mbps")

        # 计算所有下行窗口内可下行的总数据量
        total_downlink_capacity = 0.0
        valid_windows = []

        for window_idx, downlink_window in enumerate(satellite.downlink_windows):
            # 获取下行窗口的开始和结束时间
            if isinstance(downlink_window, tuple) and len(downlink_window) == 2:
                downlink_start, downlink_end = downlink_window
            else:
                try:
                    downlink_start = downlink_window.get('start', downlink_window.get('start_time'))
                    downlink_end = downlink_window.get('end', downlink_window.get('end_time'))
                    if not downlink_start or not downlink_end:
                        continue
                except:
                    # print(f"  无法解析下行窗口 #{window_idx}: {downlink_window}")
                    continue

            # 检查下行窗口是否与当前时间段重叠
            if downlink_end <= start_time or downlink_start >= end_time:
                continue

            # 计算有效下行时间段
            actual_start = max(downlink_start, start_time)
            actual_end = min(downlink_end, end_time)
            duration_seconds = (actual_end - actual_start).total_seconds()

            if duration_seconds <= 0:
                continue

            print(f"  有效下行窗口 #{window_idx}: {actual_start} 到 {actual_end}, 持续: {duration_seconds:.2f}秒")
            valid_windows.append((actual_start, actual_end, duration_seconds))

            # 计算此窗口可下行的数据量(GB)
            downlink_volume_mb = downlink_rate * duration_seconds / 8  # MB
            downlink_volume_gb = downlink_volume_mb / 1024  # GB

            print(f"  此窗口可下行: {downlink_volume_gb:.2f}GB")
            total_downlink_capacity += downlink_volume_gb

        if not valid_windows:
            print(f"  在此时间段内没有有效的下行窗口")
            return 0.0, []

        print(f"  找到{len(valid_windows)}个有效下行窗口，总下行容量: {total_downlink_capacity:.2f}GB")

        if total_downlink_capacity <= 0:
            print(f"  有效下行窗口容量为零")
            return 0.0, []

        # 按任务ID顺序下行数据（先完成的任务先下行）
        remaining_capacity = total_downlink_capacity
        task_details = []

        # 创建待下行任务的数据副本，避免修改原始列表
        tasks_to_process = stored_tasks.copy()

        for task_id in tasks_to_process:
            if task_id not in stored_task_data:
                print(f"  警告: 任务{task_id}在存储列表中，但没有数据量信息")
                continue

            task_data_volume = stored_task_data[task_id]
            task_details.append(f"{task_id}({task_data_volume:.2f}GB)")

            if remaining_capacity >= task_data_volume:
                # 整个任务数据可以下行
                downlinked_tasks.append(task_id)
                total_downlinked += task_data_volume
                remaining_capacity -= task_data_volume
                print(f"  完全下行任务{task_id}数据: {task_data_volume:.2f}GB, 剩余容量{remaining_capacity:.2f}GB")
            else:
                # 只能下行部分数据（这种情况我们不标记任务为已下行）
                break

        print(f"  待下行的任务: {', '.join(task_details) if task_details else '无'}")
        print(f"  总下行数据量: {total_downlinked:.2f}GB, 下行了{len(downlinked_tasks)}个任务: {downlinked_tasks}")
        return total_downlinked, downlinked_tasks

    def _fast_reset_satellites(self):
        """快速重置所有卫星状态到初始状态，使用字典而非列表"""
        for satellite in self.satellites:
            sat_id = satellite.sat_id
            if sat_id in self.original_satellite_states:
                # 重置状态时间线为字典
                initial_time = self.simulation_start_time
                satellite.state_timeline = {
                    initial_time: {
                        'time': initial_time,
                        'battery_level': self.original_satellite_states[sat_id]['battery_level'],
                        'current_storage': self.original_satellite_states[sat_id]['current_storage'],
                        'attitude': self.original_satellite_states[sat_id]['attitude']
                    }
                }

                # 清空任务列表
                if hasattr(satellite, 'tasks'):
                    satellite.tasks = []
            else:
                # 如果没有缓存，则使用标准重置
                satellite.reset_state()

        # 清除冲突检测缓存
        self.conflict_cache = {}

    def solve(self, num_ants=3, max_iterations=1, alpha=1.0, beta=2.0, evaporation_rate=0.5,
              heuristic_weight=1.0, parallel=False):
        """
        执行蚁群算法优化，获取任务调度结果

        Args:
            num_ants: 蚂蚁数量
            max_iterations: 最大迭代次数
            alpha: 信息素重要程度参数
            beta: 启发式因子重要程度参数
            evaporation_rate: 信息素蒸发系数
            heuristic_weight: 启发式信息权重
            parallel: 是否启用并行计算

        Returns:
            优化后的调度结果列表
        """
        start_time = time.time()
        print(f"初始化蚁群算法，任务数量: {len(self.tasks)}, 卫星数量: {len(self.satellites)}")

        # 初始化最佳方案
        best_solution = []
        best_fitness = 0.0

        # 生成启发式信息
        heuristic_info = self._build_heuristic_info()

        # 迭代优化
        for iteration in range(max_iterations):
            iteration_start = time.time()

            # 并行处理蚂蚁的路径构建
            if parallel and num_ants >= 10:
                num_processes = min(cpu_count(), 8)
                with Pool(processes=num_processes) as pool:
                    ant_args = [(alpha, beta, heuristic_info, heuristic_weight) for _ in range(num_ants)]
                    ant_results = pool.map(self._ant_build_solution, ant_args)
            else:
                ant_results = [self._ant_build_solution((alpha, beta, heuristic_info, heuristic_weight)) for _ in
                               range(num_ants)]

            # 找出本次迭代的最佳解
            iteration_best_fitness = 0
            iteration_best_solution = []
            iteration_best_ant = None

            for ant_solution, ant_fitness in ant_results:
                if ant_fitness > iteration_best_fitness:
                    iteration_best_fitness = ant_fitness
                    iteration_best_solution = ant_solution
                    iteration_best_ant = ant_solution  # 保存最佳蚂蚁路径

            # 更新全局最佳解
            if iteration_best_fitness > best_fitness:
                best_fitness = iteration_best_fitness
                best_solution = iteration_best_solution

            # 更新信息素
            self._update_pheromones(ant_results, iteration_best_ant, evaporation_rate)

            # 输出当前迭代信息
            iteration_time = time.time() - iteration_start
            if (iteration + 1) % 10 == 0 or iteration == 0 or iteration == max_iterations - 1:
                print(f"迭代 {iteration + 1}/{max_iterations}: 最佳适应度 = {best_fitness:.4f}, "
                      f"迭代最佳适应度 = {iteration_best_fitness:.4f}, "
                      f"最佳调度任务数: {len(best_solution)}, 耗时: {iteration_time:.2f}秒")

        total_time = time.time() - start_time
        print(f"蚁群算法完成，最终得分: {best_fitness:.4f}, 已分配任务数: {len(best_solution)}/{len(self.tasks)}")
        print(f"总耗时: {total_time:.2f}秒，平均每次迭代耗时: {total_time / max_iterations:.2f}秒")

        self.best_schedule = best_solution
        self.best_schedule = self.update_satellite_data_storage_with_downlink(self.best_schedule)
        return self.best_schedule

    def _build_heuristic_info(self):
        """构建启发式信息（任务优先级、时间窗口大小等）"""
        heuristic = {}

        for task_id, options in self.task_satellite_feasibility.items():
            task = next((t for t in self.tasks if t.task_id == task_id), None)
            if not task:
                continue

            heuristic[task_id] = {}
            for option in options:
                satellite = option['satellite']
                tw_start = option['tw_start']
                tw_end = option['tw_end']

                # 计算时间窗口大小（越大越灵活）
                window_size = (tw_end - tw_start).total_seconds()

                # 计算启发式值（任务优先级 + 时间窗口大小）
                h_value = task.priority * 10 + window_size / 3600  # 时间窗口（小时）

                heuristic[task_id][satellite.sat_id] = h_value

        return heuristic

    def _ant_build_solution(self, args):
        """单个蚂蚁构建解决方案"""
        alpha, beta, heuristic_info, heuristic_weight = args

        # 重置卫星状态
        self._fast_reset_satellites()

        # 初始化卫星时间线（用于快速冲突检测）
        satellite_timelines = {sat.sat_id: [] for sat in self.satellites}

        # 随机排序任务处理顺序
        task_indices = list(range(len(self.tasks)))
        self.random.shuffle(task_indices)

        # 按优先级排序（高优先级优先）
        task_indices.sort(key=lambda idx: self.tasks[idx].priority, reverse=True)

        # 蚂蚁构建的解决方案
        solution = []

        # 处理每个任务
        for task_idx in task_indices:
            task = self.tasks[task_idx]

            # 获取可行选项
            options = self.task_satellite_feasibility.get(task.task_id, [])
            if not options:
                continue

            # 计算任务-卫星选择概率
            satellite_probs = []
            valid_options = []

            for option in options:
                satellite = option['satellite']
                tw_start = option['tw_start']
                tw_end = option['tw_end']
                task_duration = option['duration']

                # 检查卫星时间线冲突
                timeline = satellite_timelines.get(satellite.sat_id, [])

                # 尝试找到最早可行时间点
                earliest_start = tw_start
                is_feasible = True

                for occupied_start, occupied_end in timeline:
                    # 检查与已占用时间段的冲突
                    if earliest_start + task_duration <= occupied_start:
                        break
                    elif occupied_end > earliest_start:
                        earliest_start = occupied_end
                        # 检查新的开始时间是否还在时间窗口内
                        if earliest_start + task_duration > tw_end:
                            is_feasible = False
                            break

                if not is_feasible:
                    continue

                # 计算信息素和启发式因子
                pheromone = self.pheromone.get(task.task_id, {}).get(satellite.sat_id, 1.0)
                heuristic = heuristic_info.get(task.task_id, {}).get(satellite.sat_id, 1.0)

                # 计算概率值
                prob = (pheromone ** alpha) * (heuristic ** beta)

                satellite_probs.append(prob)
                valid_options.append((option, earliest_start))

            if not valid_options:
                continue

            # 标准化概率
            if sum(satellite_probs) > 0:
                satellite_probs = [p / sum(satellite_probs) for p in satellite_probs]
            else:
                satellite_probs = [1.0 / len(valid_options) for _ in valid_options]

            # 按概率选择卫星
            if len(valid_options) == 1 or self.random.random() < 0.9:  # 90%概率按概率选择
                # 轮盘赌选择
                cumulative_probs = np.cumsum(satellite_probs)
                r = self.random.random()
                for i, cum_prob in enumerate(cumulative_probs):
                    if r <= cum_prob:
                        selected_idx = i
                        break
                else:
                    selected_idx = 0
            else:
                # 10%概率随机选择（探索）
                selected_idx = self.random.randint(0, len(valid_options))

            selected_option, start_time = valid_options[selected_idx]
            satellite = selected_option['satellite']
            # 获取原始值
            observation_value = selected_option['observation_time']
            maneuver_value = selected_option['maneuver_duration']

            # 格式化观测时间（如果是timedelta则转换为秒）
            observation_time = observation_value.total_seconds() if isinstance(observation_value,
                                                                               timedelta) else observation_value

            # 格式化机动时间（如果是timedelta则转换为秒）
            maneuver_duration = maneuver_value.total_seconds() if isinstance(maneuver_value,
                                                                             timedelta) else maneuver_value
            task_duration = selected_option['duration']

            # 计算结束时间
            end_time = start_time + task_duration

            # 检查卫星资源约束
            state_before = satellite.get_state_at(start_time)

            # 判断是否为日照期
            is_eclipse = True
            if hasattr(satellite, 'charging_windows'):
                for charge_start, charge_end in satellite.charging_windows:
                    if max(start_time, charge_start) < min(end_time, charge_end):
                        is_eclipse = False
                        break

            # 计算任务能耗
            energy_consumption = satellite.calculate_energy_consumption(
                task, observation_time, is_eclipse
            )

            if state_before['battery_level'] < energy_consumption:
                continue

            # 检查存储空间是否足够
            data_volume =satellite.calculate_storage(task,observation_time)
            # print(f"蚁群中任务{task.task_id}图像消耗为{data_volume}")
            if (hasattr(satellite, 'data_storage') and
                    state_before['current_storage'] + data_volume > satellite.data_storage):
                continue

            # 分配任务给卫星
            success = satellite.add_task(task, start_time, end_time, observation_time)

            if success:
                # 更新时间线（用于冲突检测）
                timeline = satellite_timelines.get(satellite.sat_id, [])
                timeline.append((start_time, end_time))
                timeline.sort()
                satellite_timelines[satellite.sat_id] = timeline

                # 查找可见窗口中的最早时间
                sat_windows = task.visible_windows.get(satellite.sat_id, [])
                earliest_sat_start = None
                for window_start, window_end in sat_windows:
                    # 计算重叠区间的起始时间（取两者的最大值）
                    overlap_start = max(window_start, task.earliest_start_time)
                    if overlap_start < window_end:  # 存在有效重叠
                        if earliest_sat_start is None or overlap_start < earliest_sat_start:
                            earliest_sat_start = overlap_start

                # 记录到调度结果中
                post_task_state = satellite.get_state_at(end_time)
                battery_cost = state_before['battery_level'] - post_task_state['battery_level']
                storage_added = post_task_state['current_storage'] - state_before['current_storage']
                post_task_state['battery_level']=min(post_task_state['battery_level'],satellite.battery_capacity)
                post_task_state['battery_level'] = max(post_task_state['battery_level'], 0)
                solution.append({
                    'cluster_name': satellite.cluster_names[0] if hasattr(satellite, 'cluster_names') else '',
                    'sat_cluster_name': satellite.cluster_names if hasattr(satellite, 'cluster_names') else '',
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'sensor_type':satellite.sensor_type,
                    'satellite_id': satellite.sat_id,
                    'cloud_extent':task.cloud_extent,
                    'light_power':task.light_power,
                    'battery_cap': satellite.battery_capacity,
                    'storage_cap': satellite.data_storage,
                    'earliest_sat_start_time': earliest_sat_start,
                    'sat_windows':sat_windows,
                    'start_time': start_time,
                    'end_time': end_time,
                    'observation_time': observation_time,
                    'maneuver_duration': maneuver_duration,
                    'battery_before_task': state_before['battery_level'],
                    'battery_after_task': post_task_state['battery_level'],
                    'current_storage': post_task_state['current_storage'],
                    'storage_before_task':state_before['current_storage'],
                    'storage_added': storage_added,
                    'battery_cost': battery_cost ,
                    'priority': task.priority,
                    'target_location': task.target_location if hasattr(task, 'target_location') else '',
                    'attitude_after_task': post_task_state['attitude'].tolist(),
                    'parent_id': task.parent_task_id,
                    'parent_area': task.boundary_points,
                    'task_name': task.task_name
                })

            # 评估解决方案适应度
        fitness = self._calculate_fitness(solution)

        return solution, fitness

    def _update_pheromones(self, ant_results, best_ant, evaporation_rate):
        """更新信息素"""
        # 信息素蒸发
        for task_id in self.pheromone:
            for sat_id in self.pheromone[task_id]:
                self.pheromone[task_id][sat_id] *= (1 - evaporation_rate)

        # 所有蚂蚁更新信息素（增强探索）
        for solution, fitness in ant_results:
            for assignment in solution:
                task_id = assignment['task_id']
                sat_id = assignment['satellite_id']

                if task_id in self.pheromone and sat_id in self.pheromone[task_id]:
                    # 信息素增量与适应度正相关
                    delta = fitness / 10.0
                    self.pheromone[task_id][sat_id] += delta

        # 最佳蚂蚁额外增加信息素（精英策略）
        if best_ant:
            for assignment in best_ant:
                task_id = assignment['task_id']
                sat_id = assignment['satellite_id']

                if task_id in self.pheromone and sat_id in self.pheromone[task_id]:
                    # 精英蚂蚁的信息素增量更大
                    self.pheromone[task_id][sat_id] += 2.0

    def _build_task_satellite_feasibility(self):
        """构建任务-卫星可行性矩阵，优化以减少重复计算"""
        feasibility = {}
        task_count = 0

        # 跳过缓存（如果已存在）
        if hasattr(self, '_feasibility_cache') and self._feasibility_cache:
            print("使用缓存的可行性矩阵")
            return self._feasibility_cache

        for task in self.tasks:
            feasibility[task.task_id] = []

            for sat_info in task.available_satellites:
                if isinstance(sat_info, dict) and 'satellite' in sat_info:
                    satellite = sat_info['satellite']
                    tw_start = sat_info['tw_start']
                    tw_end = sat_info['tw_end']

                    # 传感器类型检查（仅在task.sensor_type存在且非空时执行）
                    if hasattr(task, 'sensor_type') and task.sensor_type is not None:
                        if not (hasattr(satellite, 'sensor_type') and
                                satellite.sensor_type == task.sensor_type):
                            continue

                    # 分辨率检查（仅在task.resolution存在且非空时执行）
                    if hasattr(task, 'resolution') and task.resolution is not None:
                        if not (hasattr(satellite, 'resolution_capability') and
                                satellite.resolution_capability <= task.resolution):
                            continue

                    # 计算观测时间
                    observation_time = satellite.get_observation_time(task, tw_start)
                    if observation_time is None:
                        continue

                    # 计算姿态机动时间
                    maneuver_duration = satellite.calculate_maneuver_duration(task, tw_start)

                    # 计算任务总持续时间
                    task_duration = timedelta(
                        seconds=(maneuver_duration.total_seconds() + observation_time.total_seconds()))

                    # 检查时间窗口是否足够长
                    if tw_start + task_duration > tw_end:
                        continue

                    # 记录可行的卫星和时间窗口
                    feasibility[task.task_id].append({
                        'satellite': satellite,
                        'tw_start': tw_start,
                        'tw_end': tw_end,
                        'observation_time': observation_time,
                        'maneuver_duration': maneuver_duration,
                        'task': task,  # 添加任务引用
                        'duration': task_duration  # 缓存计算的持续时间
                    })
                    task_count += 1

        # 输出可行性统计信息
        total_options = task_count
        avg_options = total_options / len(self.tasks) if self.tasks else 0
        print(f"任务-卫星可行性矩阵构建完成: 共 {total_options} 个选项, 平均每个任务 {avg_options:.2f} 个选项")

        # 检查没有可行选项的任务
        tasks_without_options = sum(1 for options in feasibility.values() if len(options) == 0)
        if tasks_without_options > 0:
            print(f"警告: 有 {tasks_without_options} 个任务没有可行的卫星选项")

        # 缓存可行性矩阵
        self._feasibility_cache = feasibility
        return feasibility
    def _calculate_fitness(self, assignments):
        """计算调度方案的适应度"""
        if not assignments:
            return 0

        # 1. 完成的任务数
        completed_tasks_count = len(assignments)

        # 2. 优先级加权完成率
        total_priority = sum(task.priority for task in self.tasks)
        completed_priority = sum(assignment['priority'] for assignment in assignments)
        priority_completion_ratio = completed_priority / total_priority if total_priority > 0 else 0

        # 3. 卫星负载均衡
        satellite_task_counts = {}
        for assignment in assignments:
            sat_id = assignment['satellite_id']
            satellite_task_counts[sat_id] = satellite_task_counts.get(sat_id, 0) + 1

        if len(satellite_task_counts) > 1:
            std_dev = self._calculate_std_dev(list(satellite_task_counts.values()))
            # 标准差越小表示分配越均衡
            balance_score = 1.0 / (1.0 + std_dev)
        else:
            balance_score = 1.0 if len(satellite_task_counts) == 1 else 0

        # 综合适应度评分（权重可根据需要调整）
        fitness = (
                self.priority_gravity * priority_completion_ratio +  # 优先级完成率
                self.completed_gravity * (completed_tasks_count / len(self.tasks)) +  # 任务完成率
                self.balance_gravity * balance_score  # 负载均衡性
        )

        return fitness

    def _calculate_std_dev(self, values):
        """计算标准差，使用NumPy优化"""
        if not values:
            return 0
        return np.std(values)
