import os
import shutil
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify, send_file
from waitress import serve
from sqlalchemy import text

from Service.ControlleService import OperationsControlCenter
from blueprint.Cluster import cluster_bp
from blueprint.Satellite import satellite_bp
from blueprint.Task import task_bp
from blueprint.User import user_bp
import extions
from config import TLE, sat_parms
from database import db
from model.UserModel import UserModel
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# 确保JSON响应中的中文正常显示
app.json.ensure_ascii = False

# 配置数据库连接
app.config.from_object('config')
# 禁用调试模式
app.config['DEBUG'] = False
# app.config['FLASK_ENV'] = "production"
# sqlalchemy初始化
db.init_app(app)

# 全局变量用于跟踪初始化状态
_initialized = False
_occ_instance = None
_occ_thread = None
has_first_true = False

def initialize_system():
    """初始化系统，确保只执行一次"""
    global _initialized, _occ_instance, _occ_thread

    # 检查是否已经初始化过（通过检查线程是否存活）
    if _occ_thread is not None and _occ_thread.is_alive():
        print("系统已经初始化，跳过重复初始化")
        return

    print("开始初始化系统...")

    # 删除之前的图片文件夹，并重新创建
    image_dir = os.path.join(os.path.dirname(__file__), 'static', 'image')
    scheduler_dir = os.path.join(os.path.dirname(__file__), 'output_plans')
    if os.path.exists(image_dir):
        shutil.rmtree(image_dir)
        os.makedirs(image_dir)
    if os.path.exists(scheduler_dir):
        shutil.rmtree(scheduler_dir)
        os.makedirs(scheduler_dir)

    with app.app_context():
        # 初始化运控中心，传递app实例
        _occ_instance = OperationsControlCenter()
        _occ_instance.app = app  # 保存app实例
        extions.occ.set_instance(_occ_instance)

        # 创建运控中心线程
        _occ_thread = Thread(target=_occ_instance.run)
        _occ_thread.daemon = True
        _occ_thread.start()

        # 数据库表操作
        # tables_to_drop = ['t_cluster_star_relation', 't_cluster']  # 要删除的表名列表
        tables_to_drop = ['t_new_task', 't_old_task', 't_cluster_star_relation', 't_cluster']  # 要删除的表名列表
        # tables_to_drop = ['t_cluster_star_relation', 't_cluster']  # 要删除的表名列表

        # 先删除所有指定的表
        for table_name in tables_to_drop:
            try:
                # 检查表是否存在
                with db.engine.connect() as conn:
                    result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                    if result.rowcount > 0:
                        db.metadata.tables[table_name].drop(db.engine)
                        print(f"成功删除表 {table_name}")
                    else:
                        print(f"警告：表 {table_name} 不存在，无需删除")
            except Exception as e:
                if "Unknown table" in str(e):
                    print(f"警告：表 {table_name} 不存在，无需删除")
                else:
                    print(f"删除表 {table_name} 时出错: {str(e)}")

        # 然后重新创建所有表
        for table_name in tables_to_drop:
            try:
                # 检查表是否存在
                with db.engine.connect() as conn:
                    result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                    if result.rowcount == 0:
                        db.metadata.tables[table_name].create(db.engine)
                        print(f"成功创建表 {table_name}")
                    else:
                        print(f"警告：表 {table_name} 已存在，无需创建")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"警告：表 {table_name} 已存在，无需创建")
                else:
                    print(f"创建表 {table_name} 时出错: {str(e)}")

        _initialized = True
        print("系统初始化完成")


# 注册蓝图
app.register_blueprint(user_bp)  # 用户蓝图
app.register_blueprint(satellite_bp)  # 卫星蓝图
app.register_blueprint(task_bp)  # 任务蓝图
app.register_blueprint(cluster_bp)  # 星簇蓝图

# 初始化系统
initialize_system()


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


# 从前端接收TLE文件
@app.route('/initTLE', methods=['POST'])
def submit_tle_file():
    # 检查是否上传了文件
    if 'file' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    # file1 = request.files['file1']
    file2 = request.files['file']

    # 检查文件是否为空
    # if file1.filename == '' or file2.filename == '':
    if file2.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 确保library目录存在
    library_dir = os.path.join(os.getcwd(), 'library')
    if not os.path.exists(library_dir):
        os.makedirs(library_dir)

    # 保存文件到library目录
    file2_path = os.path.join(library_dir, TLE)
    # file1.save(file1_path)
    file2.save(file2_path)
    # 设置提状态为True
    _occ_instance.is_submit_tle = True
    return jsonify({"message": "Files saved successfully"}), 200


#  是否已经提交TLE文件
@app.route('/isSubmitTle', methods=['GET'])
def is_submit_tle():
    print(_occ_instance.is_submit_tle)
    return jsonify({"is_submit_tle": _occ_instance.is_submit_tle}), 200


# 从前端接收初始化文件
@app.route('/initFiles', methods=['POST'])
def submit_sate_params():
    # 检查是否上传了文件
    if 'file' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    file2 = request.files['file']

    # 检查文件是否为空
    # if file1.filename == '' or file2.filename == '':
    if file2.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 确保library目录存在
    library_dir = os.path.join(os.getcwd(), 'library')
    if not os.path.exists(library_dir):
        os.makedirs(library_dir)

    # 保存文件到library目录
    file2_path = os.path.join(library_dir, sat_parms)

    # file1.save(file1_path)
    file2.save(file2_path)
    _occ_instance.is_submit_sat = True
    return jsonify({"message": "Files saved successfully"}), 200


#  是否已经提交卫星参数文件
@app.route('/isSubmitSat', methods=['GET'])
def is_submit_sat():
    return jsonify({"is_submit_sat": _occ_instance.is_submit_sat}), 200


# 接收系统参数
@app.route('/simulateParameters', methods=['POST'])
def simulate_parameters():
    """接受系统参数"""
    form = request.json
    # start_time = form['timeRanges'][0].strip().split(',')[0]
    # end_time = form['timeRanges'][0].strip().split(',')[1]
    start_time = form['date1'].strip()
    end_time = form['date2'].strip()
    start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    _occ_instance.start_time = start_time
    _occ_instance.end_time = end_time
    completed_gravity = float(form['completed_gravity'])
    balance_gravity = float(form['balance_gravity'])
    priority_gravity = float(form['priority_gravity'])
    print(start_time, end_time)
    print(f"接收到simulate参数: {completed_gravity}, {balance_gravity}, {priority_gravity}")
    _occ_instance.completed_gravity = completed_gravity
    _occ_instance.balance_gravity = balance_gravity
    _occ_instance.priority_gravity = priority_gravity

    # 设置提交状态为True
    _occ_instance.is_submit_sys = True
    return jsonify({"message": "simulate parameters received successfully"}), 200


# 是否已经提交系统参数
@app.route('/isSubmitSys', methods=['GET'])
def is_submit_sys():
    """判断是否已经提交系统参数"""
    return jsonify({"is_submit_sys": _occ_instance.is_submit_sys}), 200


# 接收卫星参数
@app.route('/networkParameters', methods=['POST'])
def network_parameters():
    form = request.json
    for payload, value in form.items():
        extions.occ.network_config[payload] = {
            'max_storage': value.get("storage", 500),
            'max_battery': value.get("battery", 5000),
            'resolution': value.get("resolution", 1),
            'pitch_angle': value.get("pitchAngle", 45),
            'side_swing_angle': value.get("sideAngle", 45),
            'stable_time': value.get("settlingTime", 10),
            'angle_velocity': value.get("angularVelocity", 1.0),
            'width_of_cloth': value.get("width", 100),
            'thickness_threshold': value.get("threshold", 800),
            'downlink_rate': value.get("downlink_rate", 4),
            'sunlight_powers': value.get("sunlight_powers", 300),
            'maneuver_powers': value.get("maneuver_powers", 500),
            'imaging_powers': value.get("imaging_powers", 700),
            'eclipse_powers': value.get("eclipse_powers", 8)
        }
    # print(form)
    for key in ("optical", "SAR", "infrared"):
        print(extions.occ.network_config[key])
    _occ_instance.is_submit_sat = True
    _occ_instance.is_random = True
    return "ok"


# 接收卫星参数列表，用于批量添加
@app.route('/networkParametersList', methods=['POST'])
def network_parameters_list():
    form = request.json
    print(form)
    for sat_dict in form.get("list"):
        print(sat_dict)
        print(sat_dict["name"])
        print(sat_dict.get("storage"))
        _occ_instance.sats_config[sat_dict["name"]] = {
            'sensor_type': sat_dict.get("loadType", "optical"),
            'max_storage': sat_dict.get("storage", 500),
            'max_battery': sat_dict.get("battery", 5000),
            'resolution': sat_dict.get("resolution", 1),
            'pitch_angle': sat_dict.get("pitchAngle", 45),
            'side_swing_angle': sat_dict.get("sideAngle", 45),
            'stable_time': sat_dict.get("settlingTime", 10),
            'angle_velocity': sat_dict.get("angularVelocity", 1.0),
            'width_of_cloth': sat_dict.get("width", 100),
            'thickness_threshold': sat_dict.get("threshold", 800),
            'downlink_rate': sat_dict.get("downlink_rate", 4),
            'sunlight_powers': sat_dict.get("sunlight_powers", 300),
            'maneuver_powers': sat_dict.get("maneuver_powers", 500),
            'imaging_powers': sat_dict.get("imaging_powers", 700),
            'eclipse_powers': sat_dict.get("eclipse_powers", 8)
        }
        print(_occ_instance.sats_config)

    # print(form)
    _occ_instance.is_submit_sat = True  # 设置提交状态为True
    _occ_instance.is_random = True  # 设置随机状态为True
    return "ok"


# 修改算法模式选择
@app.route('/changeModel', methods=['POST'])
def change_mode():
    form = request.json
    model = form
    print("接收到的信息", form)
    print(model)
    print(f"接收到算法模式: {model}")
    _occ_instance.model = model
    return jsonify({"message": f"Algorithm mode changed to {model}"}), 200


# 获取算法模式选择
@app.route('/getModel', methods=['GET'])
def get_mode():
    return jsonify({"mode": _occ_instance.model}), 200


# 获取规划算法评估
@app.route('/getPlanningEvaluation', methods=['GET'])
def get_planning_evaluation():
    if not _occ_instance.statistical_data:
        return jsonify({"evaluation": None}), 200
    else:
        evaluation = _occ_instance.statistical_data
        # del _occ_instance.statistical_data[0]
    return jsonify({"evaluation": evaluation}), 200


# 获取星簇数据
@app.route('/getClusterData/<string:cluster_name>', methods=['GET'])
def get_cluster_data(cluster_name):
    if not _occ_instance.cluster_data:
        return jsonify({"cluster_data": None}), 200
    else:
        data = []
        for cluster_data in _occ_instance.cluster_data:
            data.append({
                "time": cluster_data["time"],
                "status": cluster_data[cluster_name]
            })
        return jsonify({"data": data}), 200


# 导出TLE文件
@app.route('/exportTleFile', methods=['GET'])
def export_tle_file():
    try:
        tle_path = os.path.join(os.getcwd(), 'library', TLE)
        if os.path.exists(tle_path):
            return send_file(tle_path,
                             as_attachment=True,
                             download_name='TLE.txt',
                             mimetype='text/plain')
        else:
            return jsonify({'error': 'TLE文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 改变时间倍速
@app.route('/changeTimeMultiple', methods=['POST'])
def accelerate_time():
    data = request.form.get("time_multiple")
    time_multiple = int(data)
    print(f"接收到加速时间倍速: {time_multiple}")
    # _occ_instance.time_multiple = time_multiple
    return jsonify({"message": f"Accelerated time by {time_multiple} multiple"}), 200


# 导出各种方案文件
@app.route('/exportSchedule/<string:filename>', methods=['POST'])
def download_file(filename):
    # if _occ_instance.algorithm_name is not None:
    #     str_name = None
    #     if filename == "greedy":
    #         filename = "greedy.xlsx"
    #         str_name = "贪心算法方案.xlsx"
    #     if filename == "ant":
    #         filename = "ant_colony.xlsx"
    #         str_name = "蚁群算法方案.xlsx"
    #     if filename == "genetic":
    #         filename = "genetic.xlsx"
    #         str_name = "遗传算法方案.xlsx"
    #     if filename == "schedule":
    #         filename = f"{_occ_instance.algorithm_name}.xlsx"
    #         str_name = "所选方案.xlsx"
    #     path = os.path.join(os.getcwd(), 'output_plans', filename)
    #     return send_file(path,
    #                      as_attachment=True,
    #                      download_name=str_name,
    #                      mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # else:
    #     return jsonify({"error": "No algorithm has been selected yet."}), 404
    if _occ_instance.algorithm_name is not None:
        str_name = None
        if filename == "greedy":
            filename = "greedy.txt"
            str_name = "贪心算法方案.txt"
        if filename == "ant":
            filename = "ant_colony.txt"
            str_name = "蚁群算法方案.txt"
        if filename == "genetic":
            filename = "genetic.txt"
            str_name = "遗传算法方案.txt"
        if filename == "schedule":
            filename = f"{_occ_instance.algorithm_name}.txt"
            str_name = "所选方案.txt"

        # 获取number参数
        number = request.json.get('number', None)
        if number:
            path = os.path.join(os.getcwd(), 'output_plans', str(number), filename)
        else:
            path = os.path.join(os.getcwd(), 'output_plans', filename)

        # 检查文件是否存在
        if not os.path.exists(path):
            return jsonify({"error": "文件不存在"}), 404

        return send_file(path,
                         as_attachment=True,
                         download_name=str_name,
                         mimetype='text/plain')
    else:
        return jsonify({"error": "没有方案"}), 404


# 查询是否有方案
@app.route('/exportScheduleStatus', methods=['GET'])
def has_schedule():
    if _occ_instance.algorithm_name is not None:
        return jsonify({"status": True}), 200
    else:
        return jsonify({"status": False}), 200


# 登录
@app.route('/login/', methods=['POST'])
def login():
    form = request.json
    print(form)
    user_model = UserModel.query.all()
    if not user_model:
        user = UserModel(name="admin", password="123456")
        db.session.add(user)
        db.session.commit()
    user = UserModel.query.filter_by(name=form["username"]).first()
    if user:
        # print("afaswfe", user.name, user.password)
        if form["username"] == user.name and form["password"] == user.password:
            return jsonify({"meta": {"status": 200}, "data": {"username": "admin",
                                                              "token": "123456789",
                                                              "user_id": 123456,
                                                              "img_url": "https://www.baidu.com/img/PCtm_dceaafbe9ae9476361eb2c8cbecbbfc.png",
                                                              "jianjie": "这是一个测试图片，用于测试", "isAdmin": 1}})
        else:
            return jsonify({"message": "用户名或密码错误"}), 401
    else:
        # print("asdf")
        return jsonify({"message": "用户名或密码错误"}), 401


# 更改用户密码
@app.route('/updatePassword', methods=['POST'])
def update_password():
    form = request.json
    print(form)
    username = form["username"]
    password = form["password"]
    user = UserModel.query.all()[0]
    if user:
        user.password = password
        user.name = username
        db.session.commit()
        return jsonify({"message": "修改成功"})
    else:
        return jsonify({"message": "修改失败"}), 401


# 查询当前系统时间
@app.route('/getCurrentTime', methods=['GET'])
def get_current_time():
    return jsonify({"current_time": str(_occ_instance.now_time),
                    "start_time": str(_occ_instance.start_time)}), 200


# 查询系统状态
@app.route('/initializationStatus', methods=['GET'])
def get_system_state():
    return jsonify(
        {"state": True, "first": True}), 200
    # 判断是否已经初始化完成，并且是否连接全部的客户端
    global has_first_true
    # 判断是否已经初始化完成，并且是否连接全部的客户端
    if not _occ_instance.satellite_network:
        return jsonify({"state": False, "first": True}), 200

    state = _occ_instance.satellite_network.is_trace and _occ_instance.satellite_network.is_connect

    if state:
        if not has_first_true:
            has_first_true = True
            return jsonify({"state": True, "first": True}), 200
        else:
            return jsonify({"state": True, "first": False}), 200
    else:
        return jsonify({"state": False, "first": True}), 200


# 更改默认时间倍速
@app.route('/setDefaultTimeMultiple', methods=['POST'])
def set_default_time_multiple():
    default_time_multiple = request.args.get("default_time_multiple", type=int)
    print(f"接收到默认时间倍速: {default_time_multiple}")
    _occ_instance.default_speed_doubling = default_time_multiple
    return jsonify({"message": f"Default time multiple set to {default_time_multiple}"}), 200


if __name__ == '__main__':
    try:
        print("正在启动服务器...")
        print("服务器启动在 http://localhost:5001")
        # server = pywsgi.WSGIServer(('0.0.0.0', 12345), app)
        # server.serve_forever()
        serve(app, host="0.0.0.0", port=5001, threads=4)  # 移除debug=True，添加threads参数
    except Exception as e:
        print(f"启动服务器时发生错误: {str(e)}")
