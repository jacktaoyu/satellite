import os
import secrets
import shutil
import threading
from datetime import datetime, timedelta, timezone
from threading import Thread
from flask import Flask, request, jsonify, send_file
from waitress import serve
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash

from Service.ControlleService import OperationsControlCenter
from blueprint.Cluster import cluster_bp
from blueprint.Satellite import satellite_bp
from blueprint.Statistics import statistics_bp
from blueprint.Task import task_bp
from blueprint.User import user_bp
import extions
from config import TLE, sat_parms
from database import db
from model.UserModel import UserModel
from flask_cors import CORS

app = Flask(__name__)
# CORS 允许来源从环境变量 CORS_ORIGINS 读取（逗号分隔），默认放行新旧前端开发地址（3000=React 版，5173=Vue 版）
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173")
CORS(app, origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()])
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
# 保护上述模块级标志读写的锁（避免并发请求/初始化线程竞争）
_state_lock = threading.Lock()

def initialize_system():
    """初始化系统，确保只执行一次"""
    global _initialized, _occ_instance, _occ_thread

    # 检查是否已经初始化过（加锁避免并发重复初始化）
    with _state_lock:
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
        # 初始化运控中心，传递app实例（加锁保护模块级标志的写入）
        with _state_lock:
            _occ_instance = OperationsControlCenter()
            _occ_instance.app = app  # 保存app实例
            extions.occ.set_instance(_occ_instance)

            # 创建运控中心线程
            _occ_thread = Thread(target=_occ_instance.run)
            _occ_thread.daemon = True
            _occ_thread.start()

        # 数据库表操作：仅创建不存在的表，保留已有数据
        tables_to_create = ['t_new_task', 't_old_task', 't_cluster_star_relation', 't_cluster', 't_user', 't_case_history']
        for table_name in tables_to_create:
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(text(f"SHOW TABLES LIKE '{table_name}'"))
                    if result.rowcount == 0:
                        db.metadata.tables[table_name].create(db.engine)
                        print(f"成功创建表 {table_name}")
                    else:
                        print(f"表 {table_name} 已存在，跳过创建")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"警告：表 {table_name} 已存在，无需创建")
                else:
                    print(f"创建表 {table_name} 时出错: {str(e)}")

        with _state_lock:
            _initialized = True
        print("系统初始化完成")


# ===== 鉴权：内存 token 表（token -> {"username": str, "expiry": datetime}） =====
# 注意：token 仅保存在内存中，后端重启后全部失效，前端收到 401 后需重新登录
VALID_TOKENS = {}
TOKEN_LOCK = threading.Lock()
TOKEN_TTL_HOURS = 12


def issue_token(username):
    """签发 token 并写入内存 token 表（有效期 12 小时）"""
    token = secrets.token_hex(16)
    with TOKEN_LOCK:
        VALID_TOKENS[token] = {
            "username": username,
            "expiry": datetime.now() + timedelta(hours=TOKEN_TTL_HOURS)
        }
    return token


def check_token(token):
    """校验 token 是否存在且未过期；返回对应的 username，无效返回 None（过期 token 顺手清除）"""
    if not token:
        return None
    with TOKEN_LOCK:
        info = VALID_TOKENS.get(token)
        if not info:
            return None
        if info["expiry"] < datetime.now():
            del VALID_TOKENS[token]
            return None
        return info["username"]


def revoke_user_tokens(username):
    """使指定用户的所有已签发 token 失效（如改密后强制重新登录）"""
    with TOKEN_LOCK:
        for token in [t for t, info in VALID_TOKENS.items() if info["username"] == username]:
            del VALID_TOKENS[token]


def parse_user_type(value):
    """容错解析 user_type，脏数据按普通用户(1)处理，避免 int() 抛异常导致 500"""
    try:
        return int(value or 1)
    except (TypeError, ValueError):
        return 1


# 无需登录即可访问的白名单路径
AUTH_WHITELIST = ('/login/', '/register/', '/statistics', '/getCurrentTime')

# 管理员专属操作路径前缀（普通用户登录后仅保留查询/导出等只读能力）
ADMIN_PATH_PREFIXES = (
    '/initTLE', '/initFiles', '/simulateParameters', '/changeModel',
    '/networkParameters',
    '/satellites/setSatelliteProperty', '/satellites/setUnavailable', '/satellites/setAvailable',
    '/satellites/setSatelliteUnavailable', '/satellites/setSatelliteAvailable',
    '/tasks/addTasks', '/tasks/addSingleTask', '/tasks/updateTask', '/tasks/deleteTask',
    '/tasks/startTask', '/tasks/pauseTask', '/tasks/manualEndTask',
    '/tasks/pointTargetCase', '/tasks/areaTargetCase', '/tasks/oceanTargetCase',
    '/clusters/addCluster', '/clusters/updateCluster', '/clusters/deleteClusterById',
    '/clusters/submitClusterFile', '/clusters/setUnavailableCluster', '/clusters/setAvailableCluster',
    '/clusters/replan',
)


@app.before_request
def global_auth_check():
    """全局鉴权：除白名单、OPTIONS 预检、静态资源外的所有请求都要求有效的 Ac-Token"""
    if request.method == 'OPTIONS':
        return None  # CORS 预检请求直接放行
    path = request.path
    if path in AUTH_WHITELIST or path.startswith('/static/') or path == '/favicon.ico':
        return None
    username = check_token(request.headers.get('Ac-Token'))
    if username is None:
        return jsonify({"meta": {"status": 401, "message": "未登录或登录已过期"}}), 401
    # 角色鉴权：管理员专属操作仅允许 user_type=1 的账号调用
    # 按路径边界匹配（精确相等或以“前缀+/”开头），避免 /tasks/addTasksWhatever 之类误伤
    if any(path == prefix or path.startswith(prefix.rstrip('/') + '/') for prefix in ADMIN_PATH_PREFIXES):
        user = UserModel.query.filter_by(name=username).first()
        if not user or parse_user_type(user.user_type) != 1:
            return jsonify({"meta": {"status": 403, "message": "无权限执行该操作，仅管理员可用"}}), 403
    return None


# 注册蓝图
app.register_blueprint(user_bp)  # 用户蓝图
app.register_blueprint(satellite_bp)  # 卫星蓝图
app.register_blueprint(task_bp)  # 任务蓝图
app.register_blueprint(cluster_bp)  # 星簇蓝图
app.register_blueprint(statistics_bp)  # 统计蓝图


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
    if _occ_instance:
        _occ_instance.is_submit_tle = True
        _occ_instance.czml_data = None  # TLE重新上传，CZML缓存失效
    return jsonify({"message": "Files saved successfully"}), 200


#  是否已经提交TLE文件
@app.route('/isSubmitTle', methods=['GET'])
def is_submit_tle():
    if _occ_instance is None:
        return jsonify({"is_submit_tle": False}), 200
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
    if _occ_instance is None:
        return jsonify({"is_submit_sat": False}), 200
    return jsonify({"is_submit_sat": _occ_instance.is_submit_sat}), 200


# 接收系统参数
@app.route('/simulateParameters', methods=['POST'])
def simulate_parameters():
    """接受系统参数"""
    form = request.json
    if not form:
        return jsonify({"error": "请求体不能为空"}), 400
    # start_time = form['timeRanges'][0].strip().split(',')[0]
    # end_time = form['timeRanges'][0].strip().split(',')[1]
    date1 = form.get('date1')
    date2 = form.get('date2')
    if not date1 or not date2:
        return jsonify({"error": "缺少date1或date2参数"}), 400
    try:
        start_time = datetime.strptime(date1.strip(), '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(date2.strip(), '%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        return jsonify({"error": "date1/date2格式错误，应为%Y-%m-%d %H:%M:%S"}), 400
    # 前端传入为本地时间，入口统一转 UTC（naive.astimezone 在 Python3.6+ 按系统本地时区解释）；
    # 转完保持 naive 交给下游（下游自行 replace(tzinfo=utc) 视为 UTC）
    start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
    end_time = end_time.astimezone(timezone.utc).replace(tzinfo=None)
    _occ_instance.start_time = start_time
    _occ_instance.end_time = end_time
    # 提交新仿真参数时，将仿真当前时钟重置为新的起始时间（加锁避免与运控主循环/网络线程并发写）
    with _occ_instance.task_lock:
        _occ_instance.now_time = start_time
        if _occ_instance.satellite_network:
            _occ_instance.satellite_network.now_time = start_time
    _occ_instance.czml_data = None  # 仿真时间变更，CZML缓存失效
    try:
        completed_gravity = float(form['completed_gravity'])
        balance_gravity = float(form['balance_gravity'])
        priority_gravity = float(form['priority_gravity'])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "权重参数缺失或不是合法数值"}), 400
    print(start_time, end_time)
    print(f"接收到simulate参数: {completed_gravity}, {balance_gravity}, {priority_gravity}")
    _occ_instance.completed_gravity = completed_gravity
    _occ_instance.balance_gravity = balance_gravity
    _occ_instance.priority_gravity = priority_gravity

    # 设置提交状态为True
    if _occ_instance:
        _occ_instance.is_submit_sys = True
    return jsonify({"message": "simulate parameters received successfully"}), 200


# 是否已经提交系统参数
@app.route('/isSubmitSys', methods=['GET'])
def is_submit_sys():
    """判断是否已经提交系统参数"""
    if _occ_instance is None:
        return jsonify({"is_submit_sys": False}), 200
    return jsonify({"is_submit_sys": _occ_instance.is_submit_sys}), 200


# 接收卫星参数
@app.route('/networkParameters', methods=['POST'])
def network_parameters():
    form = request.get_json(silent=True)
    if not isinstance(form, dict):
        return jsonify({"error": "请求体不能为空或不是合法的JSON对象"}), 400
    # 三类载荷（optical/SAR/infrared）必须齐全且为对象，否则下游网络配置缺省会抛 KeyError
    missing = [key for key in ("optical", "SAR", "infrared") if not isinstance(form.get(key), dict)]
    if missing:
        return jsonify({"error": f"缺少载荷参数（需为对象）: {', '.join(missing)}"}), 400
    for payload, value in form.items():
        if not isinstance(value, dict):
            continue
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
        print(extions.occ.network_config.get(key))
    if _occ_instance:
        _occ_instance.is_submit_sat = True
        _occ_instance.is_random = True
    return jsonify({"message": "ok"})


# 接收卫星参数列表，用于批量添加
@app.route('/networkParametersList', methods=['POST'])
def network_parameters_list():
    form = request.json
    print(form)
    sat_list = form.get("list") if form else None
    if sat_list is None:
        return jsonify({"error": "缺少list参数"}), 400
    for sat_dict in sat_list:
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
    # 合法模式为0-3的整数（0最优方案，1任务满足率最优，2资源利用率最大，3成像质量最高，对应schedule元组索引）
    if not isinstance(model, int) or isinstance(model, bool) or model not in (0, 1, 2, 3):
        return jsonify({"error": "非法的算法模式，应为0-3的整数"}), 400
    if _occ_instance:
        _occ_instance.model = model
    return jsonify({"message": f"Algorithm mode changed to {model}"}), 200


# 获取算法模式选择
@app.route('/getModel', methods=['GET'])
def get_mode():
    if not _occ_instance:
        return jsonify({"mode": 0}), 200
    return jsonify({"mode": _occ_instance.model}), 200


# 查询载荷网络参数配置（network_config 中三类载荷的内部键映射回前端字段名）
def _payload_config_to_front(v):
    return {
        "storage": v.get("max_storage"),
        "battery": v.get("max_battery"),
        "resolution": v.get("resolution"),
        "pitchAngle": v.get("pitch_angle"),
        "sideAngle": v.get("side_swing_angle"),
        "settlingTime": v.get("stable_time"),
        "angularVelocity": v.get("angle_velocity"),
        "width": v.get("width_of_cloth"),
        "threshold": v.get("thickness_threshold"),
        "downlink_rate": v.get("downlink_rate"),
        "sunlight_powers": v.get("sunlight_powers"),
        "maneuver_powers": v.get("maneuver_powers"),
        "imaging_powers": v.get("imaging_powers"),
        "eclipse_powers": v.get("eclipse_powers"),
    }


@app.route('/networkParameters', methods=['GET'])
def get_network_parameters():
    if not _occ_instance:
        return jsonify({"error": "OCC 未初始化"}), 400
    result = {}
    for key in ("optical", "SAR", "infrared"):
        v = _occ_instance.network_config.get(key)
        if isinstance(v, dict):
            result[key] = _payload_config_to_front(v)
    return jsonify(result)


# 切换运行模式：自主运行 / 程序控制（手动）
@app.route('/changeAutoRun', methods=['POST'])
def change_auto_run():
    form = request.get_json(silent=True)
    auto = form.get('auto') if isinstance(form, dict) else None
    if not isinstance(auto, bool):
        return jsonify({"error": "auto 应为布尔值"}), 400
    if _occ_instance:
        _occ_instance.auto_run = auto
        print(f"运行模式切换为: {'自主运行' if auto else '程序控制'}")
    return jsonify({"message": f"auto_run changed to {auto}"}), 200


# 获取运行模式
@app.route('/getAutoRun', methods=['GET'])
def get_auto_run():
    if not _occ_instance:
        return jsonify({"auto": True}), 200
    return jsonify({"auto": _occ_instance.auto_run}), 200


# 查询星簇级约束项配置
@app.route('/constraintConfig', methods=['GET'])
def get_constraint_config():
    if not _occ_instance:
        return jsonify({"constraints": []}), 200
    cfg = _occ_instance.constraint_config
    return jsonify({"constraints": [dict({"key": k}, **v) for k, v in cfg.items()]}), 200


# 更新星簇级约束项配置（启用状态与阈值，在规划输入装配处生效）
@app.route('/constraintConfig', methods=['POST'])
def set_constraint_config():
    form = request.get_json(silent=True)
    items = form.get('constraints') if isinstance(form, dict) else None
    if not isinstance(items, list):
        return jsonify({"error": "缺少 constraints 数组"}), 400
    if not _occ_instance:
        return jsonify({"error": "OCC 未初始化"}), 400
    for it in items:
        key = it.get('key')
        if key not in _occ_instance.constraint_config:
            return jsonify({"error": f"未知约束项: {key}"}), 400
        entry = _occ_instance.constraint_config[key]
        if 'enabled' in it:
            entry['enabled'] = bool(it['enabled'])
        if 'threshold' in it:
            try:
                entry['threshold'] = float(it['threshold'])
            except (TypeError, ValueError):
                return jsonify({"error": f"约束 {key} 的 threshold 不是合法数值"}), 400
            if entry['threshold'] < 0:
                return jsonify({"error": f"约束 {key} 的 threshold 不能为负"}), 400
        print(f"约束项更新: {entry['name']} enabled={entry['enabled']} threshold={entry['threshold']}{entry['unit']}")
    return jsonify({"message": "constraint config updated"}), 200


# 获取规划算法评估
@app.route('/getPlanningEvaluation', methods=['GET'])
def get_planning_evaluation():
    if not _occ_instance or not _occ_instance.statistical_data:
        return jsonify({"evaluation": None}), 200
    return jsonify({"evaluation": _occ_instance.statistical_data}), 200


# 获取星簇数据
@app.route('/getClusterData/<string:cluster_name>', methods=['GET'])
def get_cluster_data(cluster_name):
    if not _occ_instance or not _occ_instance.cluster_data:
        return jsonify({"cluster_data": None}), 200
    data = []
    for cluster_data in _occ_instance.cluster_data:
        data.append({
            "time": cluster_data["time"],
            "status": cluster_data.get(cluster_name)
        })
    return jsonify({"data": data}), 200


# 获取卫星网络 CZML 数据（动态生成，供三维可视化使用）
@app.route('/getCzml', methods=['GET'])
def get_czml():
    if not _occ_instance or not _occ_instance.satellite_network \
            or not _occ_instance.satellite_network.satellites:
        return jsonify({"error": "卫星网络未初始化，请先上传TLE文件和卫星参数"}), 400
    # 生成一次后缓存，避免每次请求重复计算轨道
    if getattr(_occ_instance, 'czml_data', None):
        return jsonify(_occ_instance.czml_data), 200
    from utils.czml_generator import generate_czml
    czml = generate_czml(_occ_instance.satellite_network.satellites,
                         _occ_instance.start_time, _occ_instance.end_time)
    _occ_instance.czml_data = czml
    return jsonify(czml), 200


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
    try:
        time_multiple = int(data)
    except (TypeError, ValueError):
        return jsonify({"error": "time_multiple必须为整数"}), 400
    if time_multiple < 1:
        return jsonify({"error": "time_multiple必须大于等于1"}), 400
    print(f"接收到加速时间倍速: {time_multiple}")
    if _occ_instance:
        _occ_instance.time_multiple = time_multiple
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
    if _occ_instance and _occ_instance.algorithm_name is not None:
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

        # 获取number参数，必须为大于等于0的整数，禁止字符串拼路径
        form = request.get_json(silent=True)
        if form is None:
            return jsonify({"error": "请求体不能为空或不是合法的JSON"}), 400
        number = form.get('number', None)
        if number is not None:
            try:
                number = int(number)
            except (TypeError, ValueError):
                return jsonify({"error": "number必须为整数"}), 400
            if number < 0:
                return jsonify({"error": "number必须大于等于0"}), 400
        if number:
            path = os.path.join(os.getcwd(), 'output_plans', str(number), filename)
        else:
            # 未指定批次号时，自动取 output_plans 下最新的批次目录（按目录名数字最大）
            plans_root = os.path.join(os.getcwd(), 'output_plans')
            batch_dirs = []
            if os.path.isdir(plans_root):
                batch_dirs = [d for d in os.listdir(plans_root)
                              if os.path.isdir(os.path.join(plans_root, d)) and d.isdigit()]
            if batch_dirs:
                latest_batch = max(batch_dirs, key=int)
                path = os.path.join(plans_root, latest_batch, filename)
            else:
                path = os.path.join(plans_root, filename)

        # 检查文件是否存在
        if not os.path.exists(path):
            return jsonify({"error": "暂无规划方案数据，请先执行任务规划"}), 404

        return send_file(path,
                         as_attachment=True,
                         download_name=str_name,
                         mimetype='text/plain')
    else:
        return jsonify({"error": "没有方案"}), 404


# 查询是否有方案
@app.route('/exportScheduleStatus', methods=['GET'])
def has_schedule():
    if _occ_instance and _occ_instance.algorithm_name is not None:
        return jsonify({"status": True}), 200
    else:
        return jsonify({"status": False}), 200


# 登录
@app.route('/login/', methods=['POST'])
def login():
    form = request.json
    if not form or not form.get("username") or not form.get("password"):
        return jsonify({"message": "用户名和密码不能为空"}), 400
    # 如果数据库为空，自动创建默认管理员账号
    if not UserModel.query.first():
        # 初始密码从环境变量 ADMIN_INIT_PASSWORD 读取；未设置时生成随机密码并打印醒目警告
        admin_initial_password = os.environ.get("ADMIN_INIT_PASSWORD")
        if not admin_initial_password:
            admin_initial_password = secrets.token_urlsafe(8)
            print("=" * 60)
            print(f"警告：未设置环境变量 ADMIN_INIT_PASSWORD，已生成随机管理员初始密码: {admin_initial_password}")
            print("请使用该密码首次登录 admin 后立即修改！")
            print("=" * 60)
        db.session.add(UserModel(name="admin", password=generate_password_hash(admin_initial_password)))
        db.session.commit()
    user = UserModel.query.filter_by(name=form.get("username", "")).first()
    if user:
        # 兼容历史明文密码：验证通过后自动升级为哈希存储
        if user.password.startswith(('scrypt:', 'pbkdf2:')):
            password_ok = check_password_hash(user.password, form["password"])
        else:
            password_ok = form["password"] == user.password
            if password_ok:
                user.password = generate_password_hash(form["password"])
                db.session.commit()
        if form["username"] == user.name and password_ok:
            # 校验登录时选择的用户类型与账号实际类型一致（1=管理员，其余均为普通用户）
            selected_type = (form.get("value") or "").strip()
            if selected_type and (parse_user_type(selected_type) == 1) != (parse_user_type(user.user_type) == 1):
                return jsonify({"message": "账号类型与所选用户类型不匹配"}), 401
            token = issue_token(user.name)
            return jsonify({"meta": {"status": 200}, "data": {"username": user.name,
                                                              "token": token,
                                                              "user_id": user.id,
                                                              "img_url": "https://www.baidu.com/img/PCtm_dceaafbe9ae9476361eb2c8cbecbbfc.png",
                                                              "jianjie": "这是一个测试图片，用于测试", "isAdmin": parse_user_type(user.user_type)}})
        else:
            return jsonify({"message": "用户名或密码错误"}), 401
    else:
        # print("asdf")
        return jsonify({"message": "用户名或密码错误"}), 401


# 更改用户密码（需登录，且只能修改本人密码；旧密码可选，携带时才校验）
@app.route('/updatePassword', methods=['POST'])
def update_password():
    form = request.json
    if not form or not form.get("username") or not form.get("password") or not form.get("confirmPassword"):
        return jsonify({"meta": {"status": 400, "message": "用户名、新密码和确认密码不能为空"}}), 400
    username = form["username"]
    password = form["password"]
    confirm_password = form["confirmPassword"]
    # 两次输入的密码必须一致
    if password != confirm_password:
        return jsonify({"meta": {"status": 400, "message": "两次输入的密码不一致"}}), 400
    # 新密码长度不能少于6位
    if len(password) < 6:
        return jsonify({"meta": {"status": 400, "message": "新密码长度不能少于6位"}}), 400
    # 只能修改本人密码：请求头 token 对应的用户名必须与目标用户名一致
    token_user = check_token(request.headers.get('Ac-Token'))
    if token_user != username:
        return jsonify({"meta": {"status": 401, "message": "只能修改本人密码"}}), 401
    user = UserModel.query.filter_by(name=username).first()
    if user:
        # 旧密码可选：请求中携带 oldPassword 时才校验
        # 只允许与哈希比对：旧明文账号在登录时已自动升级为哈希（未升级的旧账号需先登录一次）
        old_password = form.get("oldPassword")
        if old_password is not None:
            old_ok = user.password.startswith(('scrypt:', 'pbkdf2:')) and check_password_hash(user.password, old_password)
            if not old_ok:
                return jsonify({"meta": {"status": 400, "message": "旧密码错误"}}), 400
        user.password = generate_password_hash(password)
        db.session.commit()
        # 改密成功后使该用户所有已签发 token 失效，强制重新登录
        revoke_user_tokens(username)
        return jsonify({"message": "修改成功"})
    else:
        return jsonify({"message": "用户不存在"}), 404


# 查询当前系统时间
@app.route('/getCurrentTime', methods=['GET'])
def get_current_time():
    if not _occ_instance:
        return jsonify({"current_time": "", "start_time": ""}), 200
    return jsonify({"current_time": str(_occ_instance.now_time),
                    "start_time": str(_occ_instance.start_time)}), 200


# 查询系统状态
@app.route('/initializationStatus', methods=['GET'])
def get_system_state():
    global has_first_true
    if not _occ_instance or not _occ_instance.satellite_network:
        return jsonify({"state": False, "first": True}), 200

    state = _occ_instance.satellite_network.is_trace and _occ_instance.satellite_network.is_connect

    if state:
        with _state_lock:
            if not has_first_true:
                has_first_true = True
                return jsonify({"state": True, "first": True}), 200
        return jsonify({"state": True, "first": False}), 200
    else:
        return jsonify({"state": False, "first": True}), 200


# 更改默认时间倍速
@app.route('/setDefaultTimeMultiple', methods=['POST'])
def set_default_time_multiple():
    default_time_multiple = request.args.get("default_time_multiple", type=int)
    print(f"接收到默认时间倍速: {default_time_multiple}")
    if _occ_instance:
        _occ_instance.default_speed_doubling = default_time_multiple
    return jsonify({"message": f"Default time multiple set to {default_time_multiple}"}), 200


# 用户注册
@app.route('/register/', methods=['POST'])
def register():
    form = request.json
    if not form:
        return jsonify({"meta": {"status": 400, "message": "请求体不能为空"}}), 400
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()
    # 安全：公开注册一律强制创建普通用户（user_type="0"），忽略前端传入的管理员值，防止注册提权；
    # 非法 user_type 值同样一律按普通用户处理
    user_type = "0"

    if not username or not password:
        return jsonify({"meta": {"status": 400, "message": "用户名和密码不能为空"}}), 400

    with app.app_context():
        existing = UserModel.query.filter_by(name=username).first()
        if existing:
            return jsonify({"meta": {"status": 409, "message": "用户名已存在"}}), 409

        new_user = UserModel(name=username, password=generate_password_hash(password), user_type=user_type)
        db.session.add(new_user)
        db.session.commit()

        token = issue_token(username)
        return jsonify({
            "meta": {"status": 200},
            "data": {
                "username": username,
                "user_id": new_user.id,
                "token": token,
                "img_url": "https://www.baidu.com/img/PCtm_dceaafbe9ae9476361eb2c8cbecbbfc.png",
                "jianjie": "这是一个测试图片，用于测试",
                "isAdmin": parse_user_type(user_type)
            }
        }), 200


if __name__ == '__main__':
    try:
        # 初始化系统（从模块级移入此处，避免 app 被作为模块导入时产生副作用）
        initialize_system()
        print("正在启动服务器...")
        print("服务器启动在 http://localhost:5001")
        # server = pywsgi.WSGIServer(('0.0.0.0', 12345), app)
        # server.serve_forever()
        serve(app, host="0.0.0.0", port=5001, threads=4)  # 移除debug=True，添加threads参数
    except Exception as e:
        print(f"启动服务器时发生错误: {str(e)}")
