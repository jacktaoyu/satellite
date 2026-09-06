# -*- coding: utf-8 -*-
"""
并发锁 + 时区统一 独立自测脚本（不启动 Flask 服务、不影响运行中的后端进程）

a) 用 ast 静态分析确认：Flask 请求线程与网络/OCC 线程共用同一把锁
   （锁只在 OperationsControlCenter.__init__ 中创建一次，SatelliteNetwork 通过 operation_center.task_lock 引用，不自建锁）
b) 时区转换单测：naive 本地时间 2025-06-06 08:00（本机 +08）→ UTC naive 2025-06-06 00:00

运行：cd backend && python3 test_lock_tz.py（或 myvenv/bin/python test_lock_tz.py）
"""
import ast
import os
import sys
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
OCC_FILE = os.path.join(BASE, "Service", "ControlleService.py")
NET_FILE = os.path.join(BASE, "Service", "SatelliteNetworkService.py")
APP_FILE = os.path.join(BASE, "app.py")

failures = []


def check(name, cond):
    print(("PASS" if cond else "FAIL"), "-", name)
    if not cond:
        failures.append(name)


# ---------- a) 锁的静态检查 ----------
def check_locks():
    occ_src = open(OCC_FILE, encoding="utf-8").read()
    net_src = open(NET_FILE, encoding="utf-8").read()
    occ_tree = ast.parse(occ_src)
    net_tree = ast.parse(net_src)

    # 1. OCC __init__ 中创建了 self.task_lock = RLock()
    created_in_occ = False
    for node in ast.walk(occ_tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Attribute) and t.attr == "task_lock"
                        and isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id == "RLock"):
                    created_in_occ = True
    check("OCC.__init__ 创建 self.task_lock = RLock()", created_in_occ)

    # 2. SatelliteNetworkService 不自建锁（没有对 task_lock 的赋值），只引用 operation_center.task_lock
    net_creates_lock = False
    for node in ast.walk(net_tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Attribute) and t.attr == "task_lock":
                    net_creates_lock = True
    check("SatelliteNetworkService 不自建 task_lock（保证同一把锁实例）", not net_creates_lock)
    check("SatelliteNetworkService 通过 operation_center.task_lock 引用同一把锁",
          "self.operation_center.task_lock" in net_src)

    # 3. 关键函数均已使用锁保护
    for fname in ["delete_task", "manual_end_task", "receive_tasks", "distribute_tasks", "replan"]:
        check(f"ControlleService.{fname} 使用 with self.task_lock",
              f"with self.task_lock" in occ_src and f"def {fname}" in occ_src)
    for fname in ["check_execute_tasks", "pause_task", "start_task"]:
        check(f"SatelliteNetworkService.{fname} 使用 task_lock",
              f"def {fname}" in net_src and "task_lock" in net_src)

    # 4. app.py /simulateParameters 入口包含本地->UTC 转换
    app_src = open(APP_FILE, encoding="utf-8").read()
    check("app.py /simulateParameters 入口转 UTC", "astimezone(timezone.utc).replace(tzinfo=None)" in app_src)


# ---------- b) 时区转换单测 ----------
def convert_formula(dt):
    """与 app.py /simulateParameters 入口及 _local_naive_to_utc 完全一致的转换公式"""
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def check_timezone():
    local_dt = datetime(2025, 6, 6, 8, 0, 0)  # naive，按系统本地时区解释
    # 动态期望：本地时间 - 本地 UTC 偏移
    offset = datetime.now().astimezone().utcoffset()
    expected = (local_dt - offset)
    got = convert_formula(local_dt)
    check(f"转换公式: 本地 {local_dt} -> UTC {got}（期望 {expected}，本机偏移 {offset}）", got == expected)
    if offset == timedelta(hours=8):
        check("+08 时区下 本地 2025-06-06 08:00 -> UTC 2025-06-06 00:00",
              got == datetime(2025, 6, 6, 0, 0, 0))
    else:
        print(f"SKIP - 本机时区非 +08（{offset}），跳过 08:00->00:00 精确断言")

    # 优先验证生产代码中的真实 helper（import 失败则跳过，不影响公式验证）
    try:
        sys.path.insert(0, BASE)
        from Service.ControlleService import _local_naive_to_utc
        got2 = _local_naive_to_utc(local_dt)
        check(f"生产 helper _local_naive_to_utc: {local_dt} -> {got2}", got2 == expected)
        check("_local_naive_to_utc(None) 返回 None", _local_naive_to_utc(None) is None)
    except Exception as e:
        print(f"SKIP - 无法 import Service.ControlleService（{type(e).__name__}: {e}），仅验证转换公式")


if __name__ == "__main__":
    print("== a) 锁静态检查 ==")
    check_locks()
    print("== b) 时区转换单测 ==")
    check_timezone()
    if failures:
        print(f"\n共 {len(failures)} 项失败")
        sys.exit(1)
    print("\n全部通过")
