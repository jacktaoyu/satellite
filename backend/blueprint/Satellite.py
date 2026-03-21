import ast
import os
from datetime import datetime

from flask import Blueprint, request, send_file, jsonify
from sqlalchemy import not_, and_
from database import db
from extions import occ
from model.TaskModel import NewTaskModel, OldTaskModel

# 创建卫星蓝图对象
satellite_bp = Blueprint('satellite', __name__, url_prefix='/satellites')


# 根据卫星id查询卫星详情
@satellite_bp.route('/getSatelliteById/<int:id>', methods=['GET'])
def get_satellite_by_id(id):
    satellite = None
    for sat_name, sat in occ.satellite_network.satellites.items():
        if sat.sat_id == id:
            satellite = sat
            break

    result = {
        "id": satellite.sat_id,
        "name": satellite.sat_name,
        "orbit": satellite.alias,  # 卫星别名
        # "orbit": occ.satellite_network.orbit_info[satellite.orbit],
        "loadType": satellite.star_payload,
        "position": str([round(x, 2) for x in satellite.position]) if satellite.position is not None else "",
        "speed": str([round(x, 2) for x in satellite.speed]) if satellite.speed is not None else "",
        "sub_point": str(satellite.sub_point) if satellite.sub_point is not None else "",
        "turns": satellite.orbit_number,
        "storage": round(satellite.storage, 2),
        "battery": round(satellite.battery, 2),
        "resolution": satellite.resolution_capability,
        "width": satellite.width_of_cloth,
        "sideAngle": round(satellite.side_swing_angle, 2),
        "pitchAngle": round(satellite.pitch_angle, 2),
        "angleVelocity": round(satellite.angle_velocity, 2),
        "settlingTime": satellite.stable_time,
        "threshold": satellite.cloud_threshold,
        "status": satellite.status,
        "is_available": satellite.is_available,
        "connecting_geo": satellite.connecting_geo,
        "running_task": satellite.running_task,
        "task_num": satellite.tasks_len,
        "downlink_rate": satellite.downlink_rate,  # 下行速率
        "eclipse_powers": satellite.eclipse_powers,  # 空闲功率
        "sunlight_powers": satellite.sunlight_powers,  # 太阳能功率
        "maneuver_powers": satellite.maneuver_powers,  # 机动功率
        "imaging_powers": satellite.imaging_powers  # 成像功率
    }
    return result


# 根据卫星name查询卫星
@satellite_bp.route('/getSatelliteByName/<string:name>', methods=['GET'])
def get_satellite_by_name(name):
    satellite = None
    for sat_name, sat in occ.satellite_network.satellites.items():
        if sat_name == name:
            satellite = sat
            break
    result = {
        "id": satellite.sat_id,
        "name": satellite.sat_name,
        "orbit": satellite.orbit,
        "loadType": satellite.star_payload,
        "position": str([round(x, 2) for x in satellite.position]) if satellite.position is not None else "",
        "speed": str([round(x, 2) for x in satellite.speed]) if satellite.speed is not None else "",
        "storage": round(satellite.storage, 2),
        "battery": round(satellite.battery, 2),
        "resolution": satellite.resolution_capability,
        "width": satellite.width_of_cloth,
        "sideAngle": round(satellite.side_swing_angle, 2),
        "pitchAngle": round(satellite.pitch_angle, 2),
        "angleVelocity": satellite.angle_velocity,
        "settingTime": satellite.stable_time,
        "threshold": satellite.cloud_threshold,
        "running_task": satellite.running_task,
        "task_num": satellite.tasks_len
    }
    return result


# 查询所有卫星
@satellite_bp.route('/getAllSatellites', methods=['POST'])
def get_all_satellites():
    """
    获取所有卫星的id和name等信息
    :return:
    """
    name = request.json.get('sate_name', None)
    name = name.strip() if name else ''
    results = []
    satellites = occ.satellite_network.satellites.values()
    if name == '':
        for satellite in satellites:
            results.append({
                "id": satellite.sat_id,
                "name": satellite.sat_name,
                "storage": round(satellite.storage, 2),
                "battery": round(satellite.battery, 2),
                "resolution": satellite.resolution_capability,
                "orbit": satellite.alias,  # 卫星别名
                "loadType": satellite.star_payload
            })
        return results
    for satellite in satellites:
        if name in satellite.sat_name:
            results.append({
                "id": satellite.sat_id,
                "name": satellite.sat_name,
                "storage": round(satellite.storage, 2),
                "battery": round(satellite.battery, 2),
                "resolution": satellite.resolution_capability,
                "orbit": satellite.alias,  # 卫星别名
                "loadType": satellite.star_payload
            })
    return results


# 根据id设置某一卫星属性
@satellite_bp.route('/setSatelliteProperty/<int:id>', methods=['POST'])
def set_satellite_property(id):
    form = request.json
    max_storage = form.get('storage', 500)  # 最大存储容量,单位：M,默认500GB
    print(form.get('storage', 500))
    battery_capacity = form.get('battery', 5000)  # Wh 电池容量,默认5000Wh
    downlink_rate = form.get('downlink_rate', 4)  # 下行数据速率,单位：GB/s
    eclipse_powers = form.get('eclipse_powers', 8)  # 单位：W  空闲消耗的功率
    sunlight_powers = form.get('sunlight_powers', 300)  # 单位：W  太阳能功率
    maneuver_powers = form.get('maneuver_powers', 500)  # 单位：W  机动功率
    imaging_powers = form.get('imaging_powers', 700)  # 单位：W  成像功率
    angle_velocity = form.get('angle_velocity', 1.0)  # 单位：弧度 载荷的角度转动速度，默认1°,1/180pi
    stable_time = form.get('stable_time', 10)  # 稳定时间,默认10秒
    side_swing_angle_Max = form.get('side_swing_angle_Max', 45)  # 单位：弧度。最大侧摆角度
    pitch_angle_Max = form.get('pitch_angle_Max', 45)  # 单位：弧度。最大俯仰角度
    cloud_threshold = form.get('cloud_threshold', 800)  # 单位：km 红外不能作用的云层厚度阈值

    for sat_name, sat in occ.satellite_network.satellites.items():
        if sat.sat_id == id:
            sat.max_storage = max_storage  # 最大存储容量,单位：M,默认8TB
            sat.battery_capacity = battery_capacity  # Wh 电池容量
            sat.downlink_rate = downlink_rate  # 下行数据速率,单位：GB/s
            sat.eclipse_powers = eclipse_powers  # 单位：W  空闲消耗的功率
            sat.sunlight_powers = sunlight_powers  # 单位：W  太阳能功率
            sat.maneuver_powers = maneuver_powers  # 单位：W  机动功率
            sat.imaging_powers = imaging_powers  # 单位：W  成像功率
            sat.angle_velocity = angle_velocity  # 单位：弧度 载荷的角度转动速度，默认1°,1/180pi
            sat.stable_time = stable_time  # 稳定时间,默认10秒
            sat.side_swing_angle_Max = side_swing_angle_Max  # 单位：弧度。最大侧摆角度
            sat.pitch_angle_Max = pitch_angle_Max  # 单位：弧度。最大俯仰角度
            sat.cloud_threshold = cloud_threshold  # 单位：km 红外不能作用的云层厚度阈值
            break
    return "ok"


# 设置某一卫星不可用
@satellite_bp.route('/setUnavailable/<int:id>', methods=['GET'])
def set_unavailable(id):
    for sat_name, sat in occ.satellite_network.satellites.items():
        if sat.is_available:
            sat.is_available = False
            break
    return "ok"


# 设置某一卫星可用
@satellite_bp.route('/setAvailable/<int:id>', methods=['GET'])
def set_available(id):
    for sat_name, sat in occ.satellite_network.satellites.items():
        if not sat.is_available:
            sat.is_available = True
            break
    return "ok"


# 返回地面站信息
@satellite_bp.route('/groundStationInfo', methods=['GET'])
def ground_station_info():
    results = []
    for ground_station in occ.satellite_network.ground_stations:
        result = {
            "name": ground_station.name,
            "location": ground_station.location,
            "connecting_satellite": list(
                ground_station.connecting_satellite) if ground_station.connecting_satellite else []
        }
        results.append(result)
    return results


# 返回所有卫星信息
@satellite_bp.route('/getAllSatelliteInfo', methods=['POST'])
def all_satellite_info():
    from flask import request

    # 获取分页参数
    page_num = request.args.get('pageNum', type=int)
    page_size = request.args.get('pageSize', type=int)

    satellites = list(occ.satellite_network.satellites.values())
    total = len(satellites)

    # 如果提供了分页参数，则进行分页
    if page_num is not None and page_size is not None:
        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        satellites = satellites[start_idx:end_idx]

    results = [{
        "id": satellite.sat_id,  # 卫星ID
        "satName": satellite.sat_name,  # 卫星名
        "tle1": satellite.tle_line1,  # TLE行1
        "tle2": satellite.tle_line2,  # TLE行2
        "orbit": satellite.orbit,  # 轨道
        "connecting_geo": satellite.connecting_geo,  # 连接的高轨卫星
        "connecting_ground_station": satellite.connecting_ground_station,  # 连接的地面站
        "payload": satellite.star_payload,  # 载荷
        "startTime": satellite.simulation_start_time,  # 开始时间
        "endTime": satellite.end_time,  # 结束时间
        "position": str([round(x, 2) for x in satellite.position]) if satellite.position is not None else "",
        "speed": str([round(x, 2) for x in satellite.speed]) if satellite.speed is not None else "",
        "resolution": satellite.resolution_capability,  # 分辨率
        "width": 100000,  # 幅宽
        "height": 100000,  # 高度
        "radius": 140000,  # 半径
        "rollAngle": round(satellite.side_swing_angle, 2),  # 侧摆角度
        "pitchAngle": round(satellite.pitch_angle, 2),  # 俯仰角度
        "status": satellite.status,  # 状态
    } for satellite in satellites]

    # # 返回分页信息
    # return {
    #     "total": total,
    #     "list": results
    # }
    return results


# 根据卫星名返回信息
@satellite_bp.route('/getSatelliteInfo', methods=['POST'])
def all_satellite_info_by_name():
    """
    根据卫星名返回信息
    :return:卫星信息列表
    """
    from flask import request

    # 获取卫星名参数
    sat_name_list = request.args.get('taskSatellite', type=str)
    if sat_name_list is None or sat_name_list == '':
        return "error", 404
    sat_name_list = sat_name_list.split(',')
    satellites = occ.satellite_network.satellites.values()
    results = []
    for satellite in satellites:
        if satellite.sat_name in sat_name_list:
            results.append({
                "id": satellite.sat_id,  # 卫星ID
                "satName": satellite.sat_name,  # 卫星名
                "tle1": satellite.tle_line1,  # TLE行1
                "tle2": satellite.tle_line2,  # TLE行2
                "orbit": satellite.alias,  # 卫星别名
                "connecting_geo": satellite.connecting_geo,  # 连接的高轨卫星
                "connecting_ground_station": satellite.connecting_ground_station,  # 连接的地面站
                "payload": satellite.star_payload,  # 载荷
                "startTime": satellite.simulation_start_time,  # 开始时间
                "endTime": satellite.end_time,  # 结束时间
                "position": str([round(x, 2) for x in satellite.position]) if satellite.position is not None else "",
                "speed": str([round(x, 2) for x in satellite.speed]) if satellite.speed is not None else "",
                "resolution": satellite.resolution_capability,  # 分辨率
                "width": 100000,  # 幅宽
                "height": 100000,  # 高度
                "radius": 140000,  # 半径
                "rollAngle": round(satellite.side_swing_angle, 2),  # 侧摆角度
                "pitchAngle": round(satellite.pitch_angle, 2),  # 俯仰角度
                "status": satellite.status,  # 状态
            })

    return results


# 导出单个卫星信息
@satellite_bp.route('/exportSatelliteInfo/<int:id>', methods=['GET'])
def export_satellite_info(id):
    satellite = None
    sat_data = []
    for sat_name, sat in occ.satellite_network.satellites.items():
        if sat.sat_id == id:
            satellite = sat
            break
    sat_dict = {
        "ID": satellite.sat_id,  # 卫星ID
        "卫星名": satellite.sat_name,  # 卫星名
        "tle1": satellite.tle_line1,
        "tle2": satellite.tle_line2,
        "轨道": satellite.orbit,  # 轨道
        "载荷": satellite.star_payload,  # 载荷
        "分辨率(m)": satellite.resolution_capability,  # 分辨率
        "幅宽(km)": satellite.width_of_cloth,  # 幅宽
        "最大侧摆角度(度)": round(satellite.side_swing_angle_Max, 2),  # 侧摆角度
        "最大俯仰角度(度)": round(satellite.pitch_angle_Max, 2),  # 俯仰角度
        "载荷角度转动速度(度/s)": satellite.angle_velocity,  # 载荷角度转动速度
        "稳定时间(s)": satellite.stable_time,  # 稳定时间
        "云层厚度阈值(米)": satellite.cloud_threshold,  # 云层厚度阈值
        "下传速率(GB/s)": satellite.downlink_rate,  # 下传速率
        "空闲功率(W)": satellite.eclipse_powers,  # 空闲功率
        "太阳能功率(W)": satellite.sunlight_powers,  # 太阳能功率
        "机动功率(W)": satellite.maneuver_powers,  # 机动功率
        "成像功率(W)": satellite.imaging_powers  # 成像功率
    }
    sat_data.append(sat_dict)

    # 使用pandas创建DataFrame并导出为Excel
    import pandas as pd
    import tempfile

    df = pd.DataFrame(sat_data)

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()

    # 将数据写入Excel文件
    df.to_excel(temp_file.name, index=False, engine='openpyxl')

    # 发送文件给前端
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'{satellite.sat_name}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# 导出所有卫星信息
@satellite_bp.route('/exportAllSatelliteInfo', methods=['GET'])
def export_all_satellite_info():
    satellite = None
    sat_data = []
    for sat_name, sat in occ.satellite_network.satellites.items():
        satellite = sat
        sat_dict = {
            "ID": satellite.sat_id,  # 卫星ID
            "卫星名": satellite.sat_name,  # 卫星名
            "tle1": satellite.tle_line1,
            "tle2": satellite.tle_line2,
            "轨道": satellite.orbit,  # 轨道
            "载荷": satellite.star_payload,  # 载荷
            "分辨率(m)": satellite.resolution_capability,  # 分辨率
            "幅宽(km)": satellite.width_of_cloth,  # 幅宽
            "最大侧摆角度(度)": round(satellite.side_swing_angle_Max, 2),  # 侧摆角度
            "最大俯仰角度(度)": round(satellite.pitch_angle_Max, 2),  # 俯仰角度
            "载荷角度转动速度(度/s)": satellite.angle_velocity,  # 载荷角度转动速度
            "稳定时间(s)": satellite.stable_time,  # 稳定时间
            "云层厚度阈值(米)": satellite.cloud_threshold,  # 云层厚度阈值
            "下传速率(GB/s)": satellite.downlink_rate,  # 下传速率
            "空闲功率(W)": satellite.eclipse_powers,  # 空闲功率
            "太阳能功率(W)": satellite.sunlight_powers,  # 太阳能功率
            "机动功率(W)": satellite.maneuver_powers,  # 机动功率
            "成像功率(W)": satellite.imaging_powers  # 成像功率
        }
        sat_data.append(sat_dict)

    # 使用pandas创建DataFrame并导出为Excel
    import pandas as pd
    import tempfile

    df = pd.DataFrame(sat_data)

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    temp_file.close()

    # 将数据写入Excel文件
    df.to_excel(temp_file.name, index=False, engine='openpyxl')

    # 发送文件给前端
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name='所有卫星信息.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# 查询所有新任务
@satellite_bp.route('/getSatelliteTask', methods=['POST'])
def get_satellite_task():
    # 筛选出任务类型中没有"案例"两个字的任务
    # new_tasks = NewTaskModel.query.filter(not_(NewTaskModel.task_type.like('%案例%'))).all()
    new_tasks = NewTaskModel.query.all()
    return {"tasks": [new_task.to_dict() for new_task in new_tasks]}


# 查询第一条已经完成的任务
@satellite_bp.route('/getFinishedTask', methods=['POST'])
def get_finished_task():
    finished_task = OldTaskModel.query.filter_by(is_photo=False).first()
    if finished_task is None:
        return {"msg": "No finished task found"}
    return {"finished_task": finished_task.to_dict()}


# 查询所有已经完成的任务
@satellite_bp.route('/getAllFinishedTask', methods=['POST'])
def get_all_finished_tasks():
    # 筛选出任务类型中没有"案例"且is_photo为False的任务
    # finished_tasks = OldTaskModel.query.filter(
    #     and_(
    #         not_(OldTaskModel.task_type.like('%案例%')),
    #         OldTaskModel.is_photo == False
    #     )
    # ).all()
    finished_tasks = OldTaskModel.query.filter(OldTaskModel.is_photo==False).all()
    return {"finished_tasks": [
        finished_task.to_dict() for finished_task in finished_tasks
    ]}


# 倍速
@satellite_bp.route('/getCurrentMultiplierAndTime', methods=['GET'])
def get_current_multiplier_and_time():
    multiplier = request.args.get('multiplier', type=int)
    # current_time = request.args.get('currentTime', type=str)
    print("加速后的倍速：", multiplier)
    # print(current_time)
    # time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    # 使用strptime方法转换字符串为datetime对象
    # dt = datetime.strptime(current_time, time_format)
    # dt.replace(microsecond=0)
    # dt = dt.replace(tzinfo=None)
    occ.time_multiple = multiplier
    # occ.now_time = dt
    return "ok"


# 提供时间倍速
@satellite_bp.route('/getMultiplier', methods=['GET'])
def get_multiplier():
    return {"multiplier": occ.time_multiple}


# 保存图片路径
@satellite_bp.route('/picPath', methods=['GET'])
def save_image_path():
    task_id = request.args.get('id', type=int)
    image_path = request.args.get('path', type=str)
    old_task = OldTaskModel.query.filter_by(id=task_id).first()
    if old_task:
        old_task.is_photo = True
        string = old_task.path + f",{image_path}" if old_task.path else image_path
        if old_task.path:
            if old_task.task_type == "海洋搜救案例":
                old_task.path = string
        else:
            old_task.path = string
        db.session.commit()
        return "ok"
    return "error", 400


# 查询一条陆地案例数据
@satellite_bp.route('/getFinishedLandDemo', methods=['POST'])
def get_land_case_data():
    land_case_data = OldTaskModel.query.filter_by(task_type="陆地区域目标案例", is_photo=False).order_by(
        OldTaskModel.id.desc()).first()
    if land_case_data is None:
        return {"msg": "No finished task found"}
    occ.area = land_case_data.id
    return land_case_data.to_dict()


# 查询一条点目标案例数据
@satellite_bp.route('/getFinishedPointDemo', methods=['POST'])
def get_point_case_data():
    point_case_data = OldTaskModel.query.filter_by(task_type="点目标案例", is_photo=False).order_by(
        OldTaskModel.id.desc()).first()
    if point_case_data is None:
        return {"msg": "No finished task found"}
    occ.point = point_case_data.id
    return point_case_data.to_dict()


# 查询一条海洋案例数据
@satellite_bp.route('/getFinishedSeaMovement', methods=['POST'])
def get_ocean_case_data():
    ocean_case_data = OldTaskModel.query.filter_by(task_type="海洋搜救案例", is_photo=False).order_by(
        OldTaskModel.id.desc()).first()
    if ocean_case_data is None:
        return {"msg": "No finished task found"}
    occ.ocean = ocean_case_data.id
    return ocean_case_data.to_dict()


# 设置某一个卫星不可用
@satellite_bp.route('/setSatelliteUnavailable/<int:id>', methods=['POST'])
def set_satellite_unavailable(id):
    for satellite in occ.satellite_network.satellites.values():
        if satellite.sat_id == id:
            satellite.is_available = False
            return 'ok'
    return 'error', 400


# 设置某一个卫星可用
@satellite_bp.route('/setSatelliteAvailable/<int:id>', methods=['POST'])
def set_satellite_available(id):
    for satellite in occ.satellite_network.satellites.values():
        if satellite.sat_id == id:
            satellite.is_available = True
            return 'ok'
    return 'error', 400


# 接收前端图片二进制并保存，将图片路径保存到数据库中
@satellite_bp.route('/upload', methods=['POST'])
def download_image_binary():
    import secrets

    # 获取任务id
    task_name = request.args.get('taskName')
    if not task_name:
        return jsonify({'status': 'error', 'message': '缺少任务id'}), 400

    # 查询任务
    task = OldTaskModel.query.filter_by(task_name=task_name).first()
    if not task:
        return jsonify({'status': 'error', 'message': '未找到指定任务'}), 404

    if task.is_photo:
        return jsonify({'status': 'error', 'message': '该任务已有截图'}), 400

    # 获取上传的文件
    if 'screenshot' not in request.files:
        return jsonify({'status': 'error', 'message': '未上传文件'}), 400

    file = request.files['screenshot']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    # 判断文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
        return jsonify({'status': 'error', 'message': '不支持的文件类型'}), 400

    # 保存路径
    save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'image')
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    random_name = secrets.token_hex(8) + ext
    save_path = os.path.join(save_dir, random_name)

    print(task.task_type)
    if task.task_type == "海洋搜救案例" or task.task_type == "陆地区域目标案例":
        # data_len = task.sub_length  # 计算数据组数
        # print("data_len:", data_len)
        # # data_len = count_data_groups(task.target_location)  # 计算数据组数
        # if task.path is None or task.path == "":  # 如果路径为空
        #     path_len = 0
        # else:
        #     path_len = len(task.path.split(','))
        #
        # if path_len < data_len:  # 如果路径长度小于数据组数
        #     # 更新数据库路径
        #     if task.path is None or task.path == "":  # 如果路径为空
        #         task.path = f'static/image/{random_name}'
        #     else:
        #         task.path += f',static/image/{random_name}'
        #
        # # 如果截图到达上限，则标记为不再需要截图
        # path_len += 1
        # if path_len >= data_len:
        #     print("达到上限")
        #     task.is_photo = True

        task.path = f'static/image/{random_name}'
        print("进入了非案例")
        task.is_photo = True
    else:
        task.path = f'static/image/{random_name}'
        print("进入了非案例")
        task.is_photo = True

    # 保存文件
    file.save(save_path)

    db.session.commit()
    return jsonify({'status': 'success', 'message': '图片保存成功', 'path': task.path})


# 计算数据组数
def count_data_groups(data_str):
    try:
        data = ast.literal_eval(data_str)

        # 如果是元组列表 [(x, y), ...]
        if isinstance(data, list) and all(isinstance(item, tuple) for item in data):
            return len(data)

        # 如果是普通列表 [x, y]
        elif isinstance(data, list) and len(data) == 2:
            return 1

        else:
            return "1"

    except Exception as e:
        return 1
