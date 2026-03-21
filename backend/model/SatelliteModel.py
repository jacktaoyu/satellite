from database import db


# class SatelliteModel(db.Model):
#     """
#     卫星模型
#     """
#     __tablename__ = "t_satellite"
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键id,自增
#     sat_name = db.Column(db.String(60), nullable=False)  # 卫星名
#     sensor_type = db.Column(db.String(60), nullable=False)  # 传感器类型
#     tle_line1 = db.Column(db.String(255), nullable=False)  # 第一行TLE
#     tle_line2 = db.Column(db.String(255), nullable=False)  # 第二行TLE
#     start_time = db.Column(db.DateTime)  # 起始时间
#     end_time = db.Column(db.DateTime)  # 结束时间
#     position = db.Column(db.String(255), nullable=True)  # 卫星位置
#     speed = db.Column(db.String(255), nullable=True)  # 卫星速度
#     storage = db.Column(db.Integer, nullable=False)  # 存储余量,单位：M
#     battery = db.Column(db.Integer, nullable=False)  # 电池余量,单位：Wh
#     resolution_capability = db.Column(db.Float, nullable=False)  # 分辨率,单位：m
#     width_of_cloth = db.Column(db.Float, nullable=False)  # 幅宽,单位：km
#     side_swing_angle = db.Column(db.Float, nullable=False)  # 侧摆角度,单位：弧度
#     pitch_angle = db.Column(db.Float, nullable=False)  # 俯仰角度,单位：弧度
#     angle_velocity = db.Column(db.Float, nullable=False)  # 角度转动速度,单位：弧度
#     running_task = db.Column(db.Integer, nullable=True)  # 正在执行的任务id
