from datetime import timedelta
import numpy as np
import time
from multiprocessing import Pool, cpu_count


class GeneticAlgorithm:
    """使用遗传算法进行任务调度的优化器"""

    def __init__(self, tasks, sat_clusters, simulation_start_time=None, simulation_end_time=None,priority_gravity=3.0,balance_gravity=0.3,completed_gravity=0.5):
        """
        初始化遗传算法优化器

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
        self.priority_gravity=priority_gravity
        self.balance_gravity=balance_gravity
        self.completed_gravity=completed_gravity
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
                'attitude': initial_state['attitude']
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
                if task:
                    satellite_tasks[sat_id].append({
                        'task': task,
                        'start_time': assignment['start_time'],
                        'end_time': assignment['end_time'],
                        'observation_time': assignment.get('observation_time', 0),
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

            # print(f"\n调试信息 - 卫星{sat_id}下行处理:")

            # 初始化卫星状态
            satellite_storage = 0.0  # 卫星当前总存储量
            stored_tasks = []  # 卫星上存储的任务ID列表
            stored_task_data = {}  # 每个任务的数据量 {task_id: data_volume}
            last_task_end_time = None
            last_satellite_storage=0.0
            last_stored_tasks=[]
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
                    # print(f"  检查下行窗口: {last_task_end_time} 到 {end_time}")
                    # print(f"  当前存储量: {last_satellite_storage:.2f}GB")
                    # print(f"  存储的任务: {last_stored_tasks}")

                    # 处理在上一个任务结束到当前任务结束期间的下行
                    downlinked_data, downlinked_tasks = self._process_downlink_between_tasks_with_tasks(
                        satellite, last_task_end_time, end_time, last_satellite_storage, last_stored_tasks, stored_task_data)

                    # print(f"  下行数据量: {downlinked_data:.2f}GB, 下行任务: {downlinked_tasks}")

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

                        # print(f"  下行后剩余存储量: {satellite_storage:.2f}GB, 剩余任务: {stored_tasks}")

                    # 记录任务完成后的状态
                    task_info['assignment']['storage_after_task'] = satellite_storage
                    task_info['assignment']['stored_tasks_after_task'] = stored_tasks.copy()
                else:
                    # 第一个任务，没有前序下行
                    task_info['assignment']['storage_after_task'] = satellite_storage
                    task_info['assignment']['stored_tasks_after_task'] = stored_tasks.copy()

                # 更新最后任务完成时间
                last_task_end_time = end_time
                last_stored_tasks=stored_tasks.copy()
                last_satellite_storage=satellite_storage
            # 处理最后一个任务结束到仿真结束期间的下行
            if last_task_end_time and stored_tasks:
                simulation_end = self.simulation_end_time or (last_task_end_time + timedelta(days=1))
                # print(f"  检查最终下行窗口: {last_task_end_time} 到 {simulation_end}")
                # print(f"  最终存储量: {satellite_storage:.2f}GB")
                # print(f"  最终存储的任务: {stored_tasks}")

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

                # print(f"  仿真结束时最终存储量: {final_storage:.2f}GB, 最终存储任务: {final_stored_tasks}")

                # 记录每个任务的最终存储状态和存储的任务
                for task_info in tasks:
                    task_info['assignment']['final_storage_with_downlink'] = min(final_storage,satellite.data_storage)
                    task_info['assignment']['final_stored_tasks'] = final_stored_tasks.copy()

        # 更新并返回调度方案
        updated_schedule = [task_info['assignment'] for sat_tasks in satellite_tasks.values() for task_info in
                            sat_tasks]

        # 打印统计信息
        # print("\n下行后的卫星存储状态统计:")
        for satellite in self.satellites:
            sat_tasks = [a for a in updated_schedule if a['satellite_id'] == satellite.sat_id]
            if sat_tasks:
                sat_tasks.sort(key=lambda x: x['end_time'])
                initial_storage = sat_tasks[-1].get('storage_after_task', 0)
                final_storage = sat_tasks[-1].get('final_storage_with_downlink', initial_storage)
                final_stored_tasks = sat_tasks[-1].get('final_stored_tasks', [])
                total_tasks = len(sat_tasks)
                downlinked = initial_storage - final_storage

                # print(f"卫星{satellite.sat_id}: 执行了{total_tasks}个任务，"
                #       f"任务后存储量{initial_storage:.2f}GB，"
                #       f"下行数据量{downlinked:.2f}GB，"
                #       f"下行后最终存储量{final_storage:.2f}GB")
                # print(f"  最终存储的任务: {final_stored_tasks}")

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
        # print(
        #     f"  处理下行时间段: {start_time} 到 {end_time}, 持续时间: {(end_time - start_time).total_seconds():.2f}秒")
        # print(f"  可下行数据量: {available_storage:.2f}GB，存储任务数: {len(stored_tasks)}")

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
                except Exception as e:
                    print(f"  无法解析下行窗口 #{window_idx}: {downlink_window}: {e}")
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

            # print(f"  有效下行窗口 #{window_idx}: {actual_start} 到 {actual_end}, 持续: {duration_seconds:.2f}秒")
            valid_windows.append((actual_start, actual_end, duration_seconds))

            # 计算此窗口可下行的数据量(GB)
            downlink_volume_mb = downlink_rate * duration_seconds / 8  # MB
            downlink_volume_gb = downlink_volume_mb / 1024  # GB

            # print(f"  此窗口可下行: {downlink_volume_gb:.2f}GB")
            total_downlink_capacity += downlink_volume_gb

        if not valid_windows:
            # print(f"  在此时间段内没有有效的下行窗口")
            return 0.0, []

        # print(f"  找到{len(valid_windows)}个有效下行窗口，总下行容量: {total_downlink_capacity:.2f}GB")

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
                # print(
                #     f"  无法完整下行任务{task_id}数据: 需要{task_data_volume:.2f}GB，但剩余容量只有{remaining_capacity:.2f}GB")
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

    def solve(self, population_size=50, max_generations=1, crossover_rate=0.8,
              mutation_rate=0.2, elite_size=5, tournament_size=3, parallel=False):
        """
        执行遗传算法优化，获取任务调度结果

        Args:
            population_size: 种群大小
            max_generations: 最大迭代次数
            crossover_rate: 交叉概率
            mutation_rate: 变异概率
            elite_size: 精英个体数量
            tournament_size: 锦标赛选择的个体数量
            parallel: 是否启用并行计算

        Returns:
            优化后的调度结果列表
        """
        start_time = time.time()
        # print(f"初始化遗传算法，任务数量: {len(self.tasks)}, 卫星数量: {len(self.satellites)}")

        # 使用较少的代数可以加速
        # if max_generations > 50:
        #     print(f"注意：当前设定较高迭代次数({max_generations})可能导致较长运行时间")

        # 初始化种群
        population = self._initialize_population(population_size)

        # 评估初始种群适应度
        if parallel and population_size >= 10:
            try:
                # 启用多进程处理大种群
                num_processes = min(cpu_count(), 8)  # 限制进程数防止资源过度消耗
                with Pool(processes=num_processes) as pool:
                    fitness_schedules = pool.map(self._evaluate_chromosome, population)
                fitness_scores, schedules = zip(*fitness_schedules)
            except Exception as e:
                # daemon 线程中无法创建子进程，回退为串行执行
                print(f"多进程评估失败，回退为串行执行: {e}")
                fitness_scores, schedules = zip(*[self._evaluate_chromosome(chromosome) for chromosome in population])
        else:
            fitness_scores, schedules = zip(*[self._evaluate_chromosome(chromosome) for chromosome in population])

        # 记录最佳个体及其适应度
        best_idx = np.argmax(fitness_scores)
        best_fitness = fitness_scores[best_idx]
        best_chromosome = population[best_idx]
        self.best_schedule = schedules[best_idx]

        print(f"初始种群生成完成，最佳适应度: {best_fitness:.4f}, 任务数: {len(self.best_schedule)}")

        # 进化迭代
        gen_start_time = time.time()
        for generation in range(max_generations):
            generation_time_start = time.time()

            # 精英保留策略
            elites = []
            elite_fitness_scores = []
            elite_schedules = []

            if elite_size > 0:
                elite_indices = np.argsort(fitness_scores)[-elite_size:]
                for idx in elite_indices:
                    elites.append(population[idx])
                    elite_fitness_scores.append(fitness_scores[idx])
                    elite_schedules.append(schedules[idx])

            # 创建新一代
            new_population = elites.copy()  # 先保留精英
            new_fitness_scores = elite_fitness_scores.copy()
            new_schedules = elite_schedules.copy()

            # 生成剩余个体
            offspring_chromosomes = []
            while len(new_population) + len(offspring_chromosomes) < population_size:
                # 父代选择（锦标赛选择）
                parent1 = self._tournament_selection(population, fitness_scores, tournament_size)
                parent2 = self._tournament_selection(population, fitness_scores, tournament_size)

                # 交叉
                if self.random.random() < crossover_rate:
                    child1, child2 = self._crossover(parent1, parent2)
                else:
                    child1, child2 = parent1.copy(), parent2.copy()

                # 变异
                if self.random.random() < mutation_rate:
                    child1 = self._mutate(child1)
                if self.random.random() < mutation_rate:
                    child2 = self._mutate(child2)

                offspring_chromosomes.append(child1)
                if len(new_population) + len(offspring_chromosomes) < population_size:
                    offspring_chromosomes.append(child2)

            # 并行评估子代
            if parallel and len(offspring_chromosomes) >= 10:
                try:
                    num_processes = min(cpu_count(), 8)
                    with Pool(processes=num_processes) as pool:
                        offspring_results = pool.map(self._evaluate_chromosome, offspring_chromosomes)
                    offspring_fitness, offspring_schedules = zip(*offspring_results)
                except Exception as e:
                    # daemon 线程中无法创建子进程，回退为串行执行
                    print(f"多进程评估失败，回退为串行执行: {e}")
                    offspring_results = [self._evaluate_chromosome(chrom) for chrom in offspring_chromosomes]
                    offspring_fitness, offspring_schedules = zip(*offspring_results)
            else:
                offspring_results = [self._evaluate_chromosome(chrom) for chrom in offspring_chromosomes]
                offspring_fitness, offspring_schedules = zip(*offspring_results)

            # 添加子代到新种群
            new_population.extend(offspring_chromosomes)
            new_fitness_scores.extend(offspring_fitness)
            new_schedules.extend(offspring_schedules)

            # 更新种群
            population = new_population
            fitness_scores = new_fitness_scores
            schedules = new_schedules

            # 更新最佳个体
            generation_best_idx = np.argmax(fitness_scores)
            generation_best_fitness = fitness_scores[generation_best_idx]
            generation_best_schedule = schedules[generation_best_idx]

            if generation_best_fitness > best_fitness:
                best_fitness = generation_best_fitness
                best_chromosome = population[generation_best_idx]
                self.best_schedule = generation_best_schedule

            # 打印进度
            generation_time_end = time.time()
            generation_time = generation_time_end - generation_time_start

            if (generation + 1) % 10 == 0 or generation == 0 or generation == max_generations - 1:
                avg_fitness = sum(fitness_scores) / len(fitness_scores)
                max_tasks = max(len(s) for s in schedules) if schedules else 0
                print(f"迭代 {generation + 1}/{max_generations}: 最佳适应度 = {best_fitness:.4f}, "
                      f"平均适应度 = {avg_fitness:.4f}, 最大任务数: {max_tasks}, "
                      f"最佳调度任务数: {len(self.best_schedule)}, 耗时: {generation_time:.2f}秒")

        total_time = time.time() - start_time
        print(f"遗传算法完成，最终得分: {best_fitness:.4f}, 已分配任务数: {len(self.best_schedule)}/{len(self.tasks)}")
        print(f"总耗时: {total_time:.2f}秒，平均每代耗时: {(time.time() - gen_start_time) / max_generations:.2f}秒")
        self.best_schedule = self.update_satellite_data_storage_with_downlink(self.best_schedule)
        return self.best_schedule

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
            # print(f"task.available_satellites:{task.available_satellites}")
            for sat_info in task.available_satellites:
                if isinstance(sat_info, dict) and 'satellite' in sat_info:
                    satellite = sat_info['satellite']
                    tw_start = sat_info['tw_start']
                    tw_end = sat_info['tw_end']

                    # 动态条件检查（如果task的sensor_type/resolution为空则跳过对应检查）
                    skip = False

                    # 1. 检查传感器类型（仅当task.sensor_type非空时）
                    if hasattr(task, 'sensor_type') and task.sensor_type is not None:
                        if not (hasattr(satellite, 'sensor_type') and satellite.sensor_type == task.sensor_type):
                            print(f"载荷不满足")
                            skip = True

                    # 2. 检查分辨率（仅当task.resolution非空时）
                    if not skip and hasattr(task, 'resolution') and task.resolution is not None:
                        if not (hasattr(satellite, 'resolution_capability') and
                                satellite.resolution_capability <= task.resolution):
                            print(f"分辨率不满足")
                            skip = True

                    if skip:
                        continue

                    # 计算观测时间
                    observation_time = satellite.get_observation_time(task, tw_start)
                    if observation_time is None:
                        print(f"观测时间0")
                        continue

                    # 计算姿态机动时间
                    maneuver_duration = satellite.calculate_maneuver_duration(task, tw_start)

                    # 计算任务总持续时间
                    task_duration = maneuver_duration + observation_time

                    # 检查时间窗口是否足够长
                    if tw_start + task_duration > tw_end:
                        print(f"")
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

    def _initialize_population(self, population_size):
        """初始化种群，优化以减少重复计算"""
        population = []

        # 首先创建一个使用贪心策略的个体
        greedy_chromosome = self._create_greedy_chromosome()
        population.append(greedy_chromosome)

        # 剩余个体使用随机策略，但基于贪心染色体的一部分
        if len([gene for gene in greedy_chromosome if gene is not None]) > 0:
            # 如果贪心染色体有任务分配，基于它创建一些变种
            base_mutations = min(int(population_size * 0.2), 5)  # 最多5个或20%
            for i in range(base_mutations):
                # 从贪心染色体创建变种
                modified = greedy_chromosome.copy()
                mutation_count = max(1, int(len(self.tasks) * 0.3))  # 修改30%的任务
                indices = self.random.choice(len(self.tasks), mutation_count, replace=False)

                for idx in indices:
                    if self.random.random() < 0.7:  # 70%概率保持为None
                        modified[idx] = None
                    else:
                        modified[idx] = self._create_random_task_assignment(self.tasks[idx])

                population.append(modified)

        # 剩余个体使用完全随机策略
        remaining = population_size - len(population)
        for _ in range(remaining):
            chromosome = self._create_random_chromosome()
            population.append(chromosome)

        return population

    def _create_greedy_chromosome(self):
        """创建一个使用贪心策略的染色体，优化速度"""
        chromosome = [None] * len(self.tasks)

        # 为每个卫星创建一个时间线，用于跟踪占用情况
        satellite_timelines = {sat.sat_id: [] for sat in self.satellites}

        # 按优先级排序任务
        task_indices = list(range(len(self.tasks)))
        task_indices.sort(key=lambda i: self.tasks[i].priority, reverse=True)

        for task_idx in task_indices:
            task = self.tasks[task_idx]

            # 获取任务的可行卫星选项
            options = self.task_satellite_feasibility.get(task.task_id, [])
            if not options:
                continue

            # 评估所有可能的分配
            best_option = None
            best_start_time = None
            best_score = float('-inf')

            for option in options:
                satellite = option['satellite']
                tw_start = option['tw_start']
                tw_end = option['tw_end']
                task_duration = option['duration']  # 使用缓存的持续时间

                # 尝试找到最早可用的时间点
                earliest_start = tw_start
                timeline = satellite_timelines.get(satellite.sat_id, [])

                for occupied_start, occupied_end in timeline:
                    # 如果任务开始时间在占用期之前，且结束时间也在占用期之前，那么可以安排
                    if earliest_start + task_duration <= occupied_start:
                        break
                    # 否则，尝试安排在占用期之后
                    elif occupied_end > earliest_start:
                        earliest_start = occupied_end

                # 检查找到的时间点是否在时间窗口内
                if earliest_start + task_duration <= tw_end:
                    # 计算评分（越早执行越好）
                    time_score = -((earliest_start - tw_start).total_seconds() /
                                   (tw_end - tw_start).total_seconds() if tw_end > tw_start else 0)
                    priority_score = task.priority

                    # 综合评分
                    score = priority_score + 0.5 * time_score

                    if score > best_score:
                        best_option = option
                        best_start_time = earliest_start
                        best_score = score

            # 如果找到了一个有效的分配
            if best_option:
                satellite = best_option['satellite']
                observation_time = best_option['observation_time']
                maneuver_duration = best_option['maneuver_duration']
                task_duration = best_option['duration']
                task_end_time = best_start_time + task_duration

                # 更新卫星时间线
                timeline = satellite_timelines.get(satellite.sat_id, [])
                timeline.append((best_start_time, task_end_time))
                timeline.sort()  # 按开始时间排序
                satellite_timelines[satellite.sat_id] = timeline

                # 添加到染色体
                chromosome[task_idx] = {
                    'task': task,
                    'satellite': satellite,
                    'start_time': best_start_time,
                    'observation_time': observation_time,
                    'maneuver_duration': maneuver_duration
                }

        return chromosome

    def _create_random_task_assignment(self, task):
        """为单个任务创建随机分配"""
        options = self.task_satellite_feasibility.get(task.task_id, [])
        if not options or self.random.random() < 0.1:  # 10%概率不分配
            return None

        # 随机选择一个可行选项
        option = options[self.random.randint(0, len(options))]
        satellite = option['satellite']
        tw_start = option['tw_start']
        tw_end = option['tw_end']
        observation_time = option['observation_time']
        maneuver_duration = option['maneuver_duration']
        task_duration = option['duration']

        # 在时间窗口内随机选择一个开始时间
        max_start = tw_end - task_duration
        if max_start <= tw_start:
            return None

        # 计算合法的开始时间范围（秒）
        time_range_seconds = int((max_start - tw_start).total_seconds())

        if time_range_seconds > 0:
            offset_seconds = self.random.randint(0, time_range_seconds)
            start_time = tw_start + timedelta(seconds=offset_seconds)
        else:
            start_time = tw_start

        return {
            'task': task,
            'satellite': satellite,
            'start_time': start_time,
            'observation_time': observation_time,
            'maneuver_duration': maneuver_duration
        }

    def _create_random_chromosome(self):
        """创建一个随机染色体（调度方案），使用更高效的方法"""
        chromosome = [None] * len(self.tasks)

        # 为每个卫星创建一个时间线，用于跟踪占用情况
        satellite_timelines = {sat.sat_id: [] for sat in self.satellites}

        # 随机排序任务
        task_indices = list(range(len(self.tasks)))
        self.random.shuffle(task_indices)

        for task_idx in task_indices:
            task = self.tasks[task_idx]

            # 随机决定是否跳过任务
            if self.random.random() < 0.2:  # 20%概率不分配任务
                continue

            # 获取任务的可行卫星选项
            options = self.task_satellite_feasibility.get(task.task_id, [])
            if not options:
                continue

            # 随机选择可行选项（最多尝试3个选项）
            shuffle_options = self.random.permutation(len(options))
            max_tries = min(3, len(shuffle_options))

            for i in range(max_tries):
                option_idx = shuffle_options[i]
                option = options[option_idx]

                satellite = option['satellite']
                tw_start = option['tw_start']
                tw_end = option['tw_end']
                task_duration = option['duration']

                # 尝试最多5个随机时间点
                for _ in range(5):
                    # 计算合法的开始时间范围
                    max_start = tw_end - task_duration
                    if max_start <= tw_start:
                        continue

                    time_range_seconds = int((max_start - tw_start).total_seconds())
                    if time_range_seconds > 0:
                        offset_seconds = self.random.randint(0, time_range_seconds)
                        candidate_start = tw_start + timedelta(seconds=offset_seconds)
                    else:
                        candidate_start = tw_start

                    candidate_end = candidate_start + task_duration

                    # 检查冲突
                    timeline = satellite_timelines.get(satellite.sat_id, [])
                    is_conflict = any(candidate_start < occupied_end and candidate_end > occupied_start
                                      for occupied_start, occupied_end in timeline)

                    if not is_conflict:
                        # 更新时间线
                        timeline.append((candidate_start, candidate_end))
                        timeline.sort()
                        satellite_timelines[satellite.sat_id] = timeline

                        # 添加到染色体
                        chromosome[task_idx] = {
                            'task': task,
                            'satellite': satellite,
                            'start_time': candidate_start,
                            'observation_time': option['observation_time'],
                            'maneuver_duration': option['maneuver_duration']
                        }

                        # 找到有效分配，退出内循环
                        break

                # 如果已经分配了任务，退出选项循环
                if chromosome[task_idx] is not None:
                    break

        return chromosome

    def _evaluate_chromosome(self, chromosome):
        """评估染色体的适应度，优化执行效率"""
        # 快速重置所有卫星状态
        self._fast_reset_satellites()

        # 过滤掉None并按开始时间排序任务
        sorted_assignments = [a for a in chromosome if a is not None]
        if not sorted_assignments:
            return 0, []  # 如果没有任务分配，直接返回0适应度

        sorted_assignments.sort(key=lambda x: x['start_time'])

        # 快速冲突检测
        satellite_timelines = {sat.sat_id: [] for sat in self.satellites}
        valid_assignments = []

        for assignment in sorted_assignments:
            task = assignment['task']
            satellite = assignment['satellite']
            start_time = assignment['start_time']
            # print(f"遗传算法尝试为卫星{satellite.sat_id}添加任务，开始时间为{start_time}")
            # 获取原始值
            observation_value = assignment['observation_time']
            maneuver_value = assignment['maneuver_duration']

            # 格式化观测时间（如果是timedelta则转换为秒）
            observation_time = observation_value.total_seconds() if isinstance(observation_value,
                                                                               timedelta) else observation_value

            # 格式化机动时间（如果是timedelta则转换为秒）
            maneuver_duration = maneuver_value.total_seconds() if isinstance(maneuver_value,
                                                                             timedelta) else maneuver_value

            # 计算结束时间
            end_time = start_time + timedelta(
                seconds=(maneuver_duration + observation_time)
            )

            # 检查时间冲突
            timeline = satellite_timelines.get(satellite.sat_id, [])
            is_conflict = any(start_time < occupied_end and end_time > occupied_start
                              for occupied_start, occupied_end in timeline)

            if is_conflict:
                continue

            # 检查电池电量是否足够
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
            #print(f"遗传中中任务{task.task_id}图像消耗为{data_volume}")
            if (hasattr(satellite, 'data_storage') and
                    state_before['current_storage'] + data_volume > satellite.data_storage):
                continue

            # 分配任务给卫星
            success = satellite.add_task(task, start_time, end_time, observation_time)

            if success:
                # 更新时间线（用于冲突检测）
                timeline.append((start_time, end_time))
                timeline.sort()
                satellite_timelines[satellite.sat_id] = timeline
                sat_windows = task.visible_windows.get(satellite.sat_id, [])
                earliest_sat_start = None
                for window_start, window_end in sat_windows:
                    # 计算重叠区间的起始时间（取两者的最大值）
                    overlap_start = max(window_start, task.earliest_start_time)
                    if overlap_start < window_end:  # 存在有效重叠
                        if earliest_sat_start is None or overlap_start < earliest_sat_start:
                            earliest_sat_start = overlap_start
                # 记录到调度结果中
                battery_after_task= state_before['battery_level']-energy_consumption
                post_task_state = satellite.get_state_at(end_time)
                battery_cost=state_before['battery_level']-post_task_state['battery_level']
                post_task_state['battery_level']=min(post_task_state['battery_level'],satellite.battery_capacity)
                post_task_state['battery_level'] = max(post_task_state['battery_level'], 0)
                # print(f"卫星id{satellite.sat_id}当前{end_time}任务后的电量{post_task_state['battery_level']}，电池容量{satellite.battery_capacity}")
                storage_added=post_task_state['current_storage']-state_before['current_storage']
                # print(f"遗传算法中任务{task.task_id}执行前卫星{satellite.sat_id}存储{state_before['current_storage']}GB任务后{post_task_state['current_storage']}GB")
                valid_assignments.append({
                    'cluster_name': satellite.cluster_names[0] if hasattr(satellite, 'cluster_names') else '',
                    'sat_cluster_name': satellite.cluster_names if hasattr(satellite, 'cluster_names') else '',
                    'task_id': task.task_id,
                    'sensor_type': satellite.sensor_type,
                    'task_type':task.task_type,
                    'satellite_id': satellite.sat_id,
                    'earliest_sat_start_time':earliest_sat_start ,
                    'cloud_extent': task.cloud_extent,
                    'light_power': task.light_power,
                    'sat_windows': sat_windows,
                    'start_time': start_time,
                    'end_time': end_time,
                    'observation_time': observation_time,
                    'maneuver_duration': maneuver_duration,
                    'battery_before_task': state_before['battery_level'],
                    'battery_after_task':  post_task_state['battery_level'],
                    'current_storage': post_task_state['current_storage'],
                    'storage_before_task': state_before['current_storage'],
                    'storage_added':storage_added,
                    'battery_cap': satellite.battery_capacity,
                    'storage_cap': satellite.data_storage,
                    'battery_cost': battery_cost,
                    'priority': task.priority,
                    'target_location': task.target_location if hasattr(task, 'target_location') else '',
                    'attitude_after_task': post_task_state['attitude'].tolist(),
                    'parent_id':task.parent_task_id,
                    'parent_area':task.boundary_points,
                    'task_name':task.task_name
                })

        # 计算适应度
        fitness = self._calculate_fitness(valid_assignments)

        return fitness, valid_assignments

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

    def _tournament_selection(self, population, fitness_scores, tournament_size):
        """锦标赛选择"""
        # 随机选择tournament_size个个体
        indices = self.random.choice(len(population), min(tournament_size, len(population)), replace=False)

        # 选择适应度最高的个体
        best_idx = indices[0]
        for idx in indices[1:]:
            if fitness_scores[idx] > fitness_scores[best_idx]:
                best_idx = idx

        return population[best_idx].copy()

    def _crossover(self, parent1, parent2):
        """两点交叉操作"""
        if len(parent1) <= 2:
            return parent1.copy(), parent2.copy()

        # 选择两个交叉点
        point1 = self.random.randint(0, len(parent1) - 1)
        point2 = self.random.randint(point1 + 1, len(parent1))

        # 创建两个子代
        child1 = parent1.copy()
        child2 = parent2.copy()

        # 交换两点之间的基因
        child1[point1:point2] = parent2[point1:point2]
        child2[point1:point2] = parent1[point1:point2]

        return child1, child2

    def _mutate(self, chromosome):
        """变异操作，优化以减少计算量"""
        # 处理空染色体的情况
        if not chromosome:
            return []  # 直接返回空染色体，避免后续操作

        # 随机选择要变异的任务数量（1到20%的任务）
        num_tasks = len(chromosome)
        max_mutations = max(1, int(0.2 * num_tasks))
        num_mutations = self.random.randint(1, max_mutations + 1)

        # 随机选择任务进行变异
        task_indices = self.random.choice(num_tasks, num_mutations, replace=False)

        for task_idx in task_indices:
            # 变异策略：30%概率设为None，70%概率重新分配
            if self.random.random() < 0.3:
                chromosome[task_idx] = None
            else:
                task = self.tasks[task_idx]
                chromosome[task_idx] = self._create_random_task_assignment(task)

        return chromosome
    def _calculate_std_dev(self, values):
        """计算标准差，使用NumPy优化"""
        if not values:
            return 0
        return np.std(values)


