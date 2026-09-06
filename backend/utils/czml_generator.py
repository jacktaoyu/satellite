# -*- coding: utf-8 -*-
"""根据当前卫星网络 TLE 动态生成 CZML 数据，供前端 Cesium 三维可视化使用"""
from datetime import datetime, timedelta, timezone

from skyfield.api import EarthSatellite
from skyfield.framelib import itrs

from Service.SatelliteService import get_timescale

# 卫星图标（16x16 PNG，与原静态 wx.czml 一致）
SATELLITE_ICON = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IA"
                  "Rs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADJSURBVDhPnZHRDcMgEEMZjVEYpaNklIzSEfLfD4qN"
                  "nXAJSFWfhO7w2Zc0Tf9QG2rXrEzSUeZLOGm47WoH95x3Hl3jEgilvDgsOQUTqsNl68ezEwn1vae6lceSEEYvvWNT/Rxc4CXQNGadho"
                  "1NXoJ+9iaqc2xi2xbt23PJCDIB6TQjOC6Bho/sDy3fBQT8PrVhibU7yBFcEPaRxOoeTwbwByCOYf9VGp1BYI1BA+EeHhmfzKbBoJEQ"
                  "wn1yzUZtyspIQUha85MpkNIXB7GizqDEECsAAAAASUVORK5CYII=")

# 可视化采样间隔（秒）与轨迹拖尾时长（秒），拖尾取约 1/4 轨道周期避免全球轨道线杂乱
SAMPLE_STEP_SECONDS = 300
PATH_LEAD_TRAIL_SECONDS = 1500


def _iso(dt):
    """datetime -> CZML ISO 字符串（UTC）"""
    return dt.astimezone(timezone.utc).isoformat()


def generate_czml(satellites, start_time, end_time, step_seconds=SAMPLE_STEP_SECONDS):
    """
    由卫星字典生成 CZML 列表

    :param satellites: dict[sat_name -> Satellite]，需含 tle_line1/tle_line2
    :param start_time: 仿真开始时间（naive 视为 UTC）
    :param end_time: 仿真结束时间（naive 视为 UTC），可视化最多取开始后 24 小时
    :param step_seconds: 位置采样间隔
    :return: CZML packet 列表
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    # 可视化窗口最长取 24 小时，避免数据量过大
    viz_end = min(end_time, start_time + timedelta(days=1))

    ts = get_timescale()
    t0 = ts.from_datetime(start_time)
    t1 = ts.from_datetime(viz_end)
    sample_count = max(2, int((viz_end - start_time).total_seconds() // step_seconds) + 1)
    times = ts.linspace(t0, t1, sample_count)

    interval = f"{_iso(start_time)}/{_iso(viz_end)}"
    czml = [{
        "id": "document",
        "version": "1.0",
        "clock": {
            "currentTime": _iso(start_time),
            "multiplier": 60,
            "interval": interval,
            "range": "LOOP_STOP",
            "step": "SYSTEM_CLOCK_MULTIPLIER"
        }
    }]

    for sat_name, sat in satellites.items():
        try:
            orbit = EarthSatellite(sat.tle_line1, sat.tle_line2, sat_name, ts)
            # itrs 框架下为 ECEF（WGS84 固定系）坐标，单位米
            xyz = orbit.at(times).frame_xyz(itrs).m  # shape: (3, sample_count)
        except Exception as e:
            print(f"生成卫星 {sat_name} CZML 失败: {e}")
            continue

        cartesian = []
        for i in range(sample_count):
            cartesian.append(i * step_seconds)
            cartesian.append(float(xyz[0][i]))
            cartesian.append(float(xyz[1][i]))
            cartesian.append(float(xyz[2][i]))

        czml.append({
            "id": f"Satellite/{sat_name}",
            "description": f"Orbit of Satellite: {sat_name}",
            "availability": interval,
            "billboard": {"show": True, "image": SATELLITE_ICON, "scale": 1.5},
            "label": {
                "show": True,
                "text": sat_name,
                "horizontalOrigin": "LEFT",
                "pixelOffset": {"cartesian2": [12, 0]},
                "fillColor": {"rgba": [213, 255, 0, 255]},
                "font": "11pt Lucida Console",
                "outlineColor": {"rgba": [0, 0, 0, 255]},
                "outlineWidth": 2
            },
            "position": {
                "epoch": _iso(start_time),
                "cartesian": cartesian,
                "interpolationAlgorithm": "LAGRANGE",
                "interpolationDegree": 5,
                "referenceFrame": "FIXED"
            },
            "path": {
                "show": True,
                "width": 1,
                "leadTime": PATH_LEAD_TRAIL_SECONDS,
                "trailTime": PATH_LEAD_TRAIL_SECONDS,
                "resolution": 120,
                "material": {"solidColor": {"color": {"rgba": [255, 255, 0, 128]}}}
            }
        })

    return czml
