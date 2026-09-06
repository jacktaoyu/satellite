# config.py
import os

# 数据库配置（支持从环境变量读取，方便部署到不同环境）
USERNAME = os.environ.get("DB_USER", "root")  # 数据库登录用户名
PASSWORD = os.environ.get("DB_PASSWORD", "")  # 数据库登录密码
HOST = os.environ.get("DB_HOST", "localhost")  # 数据库服务器地址
PORT = os.environ.get("DB_PORT", "3306")  # 数据库连接端口号
DATABASE = os.environ.get("DB_NAME", "satellite")  # 要访问的数据库名称

# 构建数据库连接URI
if PASSWORD:
    DB_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?charset=utf8'
else:
    DB_URI = f'mysql+pymysql://{USERNAME}@{HOST}:{PORT}/{DATABASE}?charset=utf8'

# SQLALCHEMY_DATABASE_URI配置项，设置数据库的连接URI，让SQLAlchemy知道如何连接数据库
SQLALCHEMY_DATABASE_URI = DB_URI
# SQLALCHEMY_TRACK_MODIFICATIONS配置项，用于控制是否动态追踪对象修改情况
# 若设置为True，会追踪对象修改，但会消耗额外资源，默认不设置时会有告警提示，这里设为False关闭追踪
SQLALCHEMY_TRACK_MODIFICATIONS = False
# SQLALCHEMY_ECHO配置项，用于设置是否在查询时显示原始的SQL语句
# 设为False表示不显示原始SQL语句，设为True则会在控制台等地方输出实际执行的SQL语句，方便调试查看
SQLALCHEMY_ECHO = False

# 卫星网络配置参数

# 最大客户端连接数
NODES = 2

# 卫星功耗参数
sunlight_powers = {
    'maneuver': 50,  # 消耗功率（正值）
    'idle': 8,  # 空闲消耗功率（正值）
    'charge': 30  # 充电功率（正值）
}

INTER_VAL_TIME = 5  # 系统休眠间隔时间，默认为5秒

# 地面站配置
GROUND_STATION = {
    "新疆喀什": (39.47, 75.99),
    "重庆": (29.56, 106.55),
    "雄安": (39.04, 115.86),
    "海南文昌": (19.55, 110.79),
    "黑龙江佳木斯": (45.81, 130.37)
}
# 地面站速率，单位为Gbps
GROUND_RATE = 4

# 卫星配置文件名
TLE = "TLE.txt"
# TLE = "TLE2.txt"
# sat_parms = "sat_parameters.xlsx"
sat_parms = "satellite_info.xlsx"
# 星簇配置文件名
# cluster_parms = "clusters_parameters.xlsx"
cluster_parms = "t_cluster.xlsx"
