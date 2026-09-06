# -*- coding: utf-8 -*-
"""性能基准测试：20点目标+2区域目标+8移动目标，200星，验证24h周期规划耗时≤5分钟

兼容鉴权：先 POST /login/ 获取 token，所有请求带 Ac-Token 头。
新增任务名为服务端自动生成，无法自定义前缀；脚本通过前后快照 id 差集记录本次新增任务 id，
便于后续清理（写入结果文件）。
用法: myvenv/bin/python3 test_benchmark.py
"""
import requests
import time
import random
import sys
import json
import os
from datetime import datetime

BASE = "http://localhost:5001"
random.seed(42)

payloads = ["optical", "infrared", "SAR"]

INIT_WAIT_TIMEOUT = 600   # 等待系统初始化（is_trace）的最长时间
PLAN_TIMEOUT = 300        # 指标判定：规划耗时上限
OVERALL_TIMEOUT = 1800    # 等待全部批次规划完成的硬上限


def login():
    r = requests.post(f"{BASE}/login/", json={"username": "admin", "password": "123456"}, timeout=10)
    r.raise_for_status()
    token = r.json()["data"]["token"]
    return {"Ac-Token": token}


def make_task(i, task_type):
    lat = round(random.uniform(-60, 60), 2)
    lon = round(random.uniform(-180, 180), 2)
    if task_type == "区域目标":
        # 区域目标：给4个边界点
        coords = [f"{lat},{lon}", f"{lat},{lon+2}", f"{lat+2},{lon+2}", f"{lat+2},{lon}"]
    elif task_type == "移动目标":
        # 移动目标：给轨迹点
        coords = [f"{lat},{lon}", f"{lat+0.5},{lon+0.5}", f"{lat+1},{lon+1}"]
    else:
        coords = [f"{lat},{lon}"]
    return {
        "task_id": "",
        "priority": random.randint(1, 5),
        "is_urgent": "否",
        "type": task_type,
        "payload": payloads[i % 3],
        "resolution": 1.0,
        "timeRanges": ["2025-06-06 00:00:00,2025-06-07 00:00:00"],
        "cycle": "",
        "cloud_thickness": 0,
        "cluster_name": "",
        "appoint_time": "",
        "coordinates": coords
    }


def wait_initialized(headers):
    """等待系统初始化完成（客户端已连接且轨迹计算就绪）"""
    t0 = time.time()
    while time.time() - t0 < INIT_WAIT_TIMEOUT:
        r = requests.get(f"{BASE}/initializationStatus", headers=headers, timeout=10).json()
        if r.get("state"):
            print(f"系统已初始化（等待 {time.time()-t0:.1f}s）")
            return True
        print("系统尚未初始化完成，10s 后重试...")
        time.sleep(10)
    return False


def snapshot_task_ids(headers):
    r = requests.get(f"{BASE}/tasks/getNewTasksByCondition", headers=headers, timeout=60)
    r.raise_for_status()
    return {t["id"] for t in r.json()}


def get_evaluation(headers):
    try:
        ev = requests.get(f"{BASE}/getPlanningEvaluation", headers=headers, timeout=10).json().get("evaluation")
    except Exception:
        ev = None
    return ev or []


def print_eval_entry(latest):
    print(f"后端规划耗时 duration: {latest.get('duration'):.1f}s")
    print(f"任务满足率 task_satisfaction: {latest.get('task_satisfaction')}")
    for algo in ("greedy", "ant_colony", "genetic"):
        m = latest.get(algo) or {}
        print(f"  {algo}: 满足率={m.get('task_satisfaction')}, 资源利用率={m.get('resource_utilization')}, 成像质量={m.get('imaging_quality')}")


def main():
    headers = login()
    print("登录成功，已获取 Ac-Token")

    if not wait_initialized(headers):
        print("系统未初始化完成（等待客户端连接/轨迹计算超时），退出")
        sys.exit(1)

    baseline_ids = snapshot_task_ids(headers)
    print(f"提交前未完成任务数: {len(baseline_ids)}")
    baseline_eval_count = len(get_evaluation(headers))

    tasks = ([make_task(i, "点目标") for i in range(20)]
             + [make_task(i, "区域目标") for i in range(2)]
             + [make_task(i, "移动目标") for i in range(8)])
    print(f"提交 {len(tasks)} 个任务（20点+2区域+8移动）...")

    t0 = time.time()
    submit_ok = 0
    for t in tasks:
        resp = requests.post(f"{BASE}/tasks/addSingleTask", json=t, headers=headers, timeout=30)
        assert resp.status_code == 200, resp.text
        submit_ok += 1
    submit_elapsed = time.time() - t0
    print(f"任务提交完成（{submit_ok}/{len(tasks)}），耗时 {submit_elapsed:.1f}s，等待规划...")

    # 轮询规划结果：先等第一批新评估（基准判定用），再等队列全部消化（count 连续稳定）
    result_lines = []
    first_entry_elapsed = None
    last_count = baseline_eval_count
    stable_rounds = 0
    deadline = t0 + OVERALL_TIMEOUT
    while time.time() < deadline:
        time.sleep(10)
        ev = get_evaluation(headers)
        count = len(ev)
        if count > baseline_eval_count and first_entry_elapsed is None:
            first_entry_elapsed = time.time() - t0
            latest = ev[-1]
            print(f"\n===== 首个批次规划完成 =====")
            print(f"端到端总耗时（提交+规划）: {first_entry_elapsed:.1f}s")
            print_eval_entry(latest)
            ok = latest.get("duration", 9999) <= PLAN_TIMEOUT
            print(f"指标判定（规划≤300s）: {'✅ 达标' if ok else '❌ 超标'}")
        if count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
            last_count = count
        if first_entry_elapsed is not None and stable_rounds >= 3:
            break  # 评估数量 30s 无增长，认为所有批次已规划完
    else:
        print("❌ 超时：等待规划结果超出上限")

    new_eval = get_evaluation(headers)[baseline_eval_count:]
    new_ids = sorted(snapshot_task_ids(headers) - baseline_ids)
    total_elapsed = time.time() - t0

    print(f"\n===== 汇总 =====")
    print(f"新增评估批次数: {len(new_eval)}，全部完成总耗时: {total_elapsed:.1f}s")
    durations = [e.get("duration", 0) for e in new_eval]
    if durations:
        print(f"各批次规划耗时: 最大 {max(durations):.1f}s / 最小 {min(durations):.1f}s / 平均 {sum(durations)/len(durations):.1f}s")
    print(f"本次新增任务 id 数: {len(new_ids)}")

    # 保存验收证据
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"benchmark_result_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(f"===== 基准测试运行记录 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
        f.write(f"任务规模: 20 点目标 + 2 区域目标 + 8 移动目标 = {len(tasks)} 个\n")
        f.write(f"任务提交: {submit_ok}/{len(tasks)} 成功，耗时 {submit_elapsed:.1f}s\n")
        if first_entry_elapsed is not None:
            first = new_eval[0] if new_eval else {}
            f.write(f"首个批次: 端到端耗时 {first_entry_elapsed:.1f}s，"
                    f"后端规划耗时 duration={first.get('duration')}s，"
                    f"任务满足率={first.get('task_satisfaction')}\n")
            ok = first.get("duration", 9999) <= PLAN_TIMEOUT
            f.write(f"指标判定（规划≤300s）: {'达标' if ok else '超标'}\n")
        else:
            f.write("未在时限内获得任何规划评估结果\n")
        if durations:
            f.write(f"全部 {len(new_eval)} 个批次: 最大 {max(durations):.1f}s / "
                    f"最小 {min(durations):.1f}s / 平均 {sum(durations)/len(durations):.1f}s，"
                    f"总耗时 {total_elapsed:.1f}s\n")
        f.write(f"本次新增任务 id（可用于清理）: {json.dumps(new_ids)}\n\n")
    print(f"结果已保存到 {out_path}")


if __name__ == "__main__":
    main()
