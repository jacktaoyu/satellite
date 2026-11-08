import uuid
from datetime import datetime

from database import db


class NewTaskModel(db.Model):
    """
    新产生的任务模型
    """
    __tablename__ = "t_new_task"
    id = db.Column(db.Integer, primary_key=True)  # 主键id
    task_uuid = db.Column(db.String(36), nullable=True, unique=True,
                          default=lambda: str(uuid.uuid4()))  # 稳定业务标识
    task_name = db.Column(db.String(255), nullable=True)  # 任务名
    priority = db.Column(db.Integer, nullable=False)  # 任务的优先级
    is_emergency = db.Column(db.Boolean, default=False)  # 是否是紧急任务
    sensor_type = db.Column(db.String(255), nullable=True)  # 载荷类型
    task_type = db.Column(db.String(255), nullable=False)  # 任务类型
    resolution = db.Column(db.Float, nullable=True)  # 分辨率要求
    start_time = db.Column(db.DateTime)  # 开始时间
    end_time = db.Column(db.DateTime)  # 结束时间
    user_start_time = db.Column(db.DateTime)  # 开始时间
    user_end_time = db.Column(db.DateTime)  # 结束时间
    battery_before = db.Column(db.Text, nullable=True)  # 任务开始前电池电量
    battery_after = db.Column(db.Text, nullable=True)  # 任务结束后电池电量
    storge_before = db.Column(db.Text, nullable=True)  # 任务开始前存储空间
    storge_after = db.Column(db.Text, nullable=True)  # 任务结束后存储空间
    light_power = db.Column(db.String(255), nullable=True)  # 是否有光照
    appoint_time = db.Column(db.DateTime, nullable=True)  # 定时时间
    target_location = db.Column(db.String(255), nullable=False)  # 观测位置,[纬度, 经度]
    assigned_satellite_name = db.Column(db.String(255), nullable=True)  # 卫星名  # 任务所属的卫星，外键
    status = db.Column(db.String(255), nullable=False)  # 任务状态
    cluster_name = db.Column(db.String(255))  # 指定任务执行的星簇
    friend_task_id = db.Column(db.Integer, nullable=True)  # 合并任务id
    cloud_thickness = db.Column(db.Float, nullable=True)  # 云层厚度
    comment = db.Column(db.Text, nullable=True, default=None)  # 备注

    # parent_task_id = db.Column(db.Integer, nullable=True)  # 主任务id

    def to_dict(self):
        """将新任务模型对象转换为字典"""
        return {
            'id': self.id,  # 任务id
            'taskUuid': self.task_uuid,  # 稳定业务标识
            'taskName': self.task_name,  # 任务名
            'priority': self.priority,  # 任务优先级
            'isEmergency': self.is_emergency,  # 是否是紧急任务
            'sensorType': self.sensor_type,  # 载荷类型
            'taskType': self.task_type,  # 任务类型
            'resolution': self.resolution,  # 分辨率要求
            'startTime': str(self.start_time) if self.start_time else None,  # 开始时间
            'endTime': str(self.end_time) if self.end_time else None,  # 结束时间
            'targetLocation': self.target_location,  # 目标位置
            'assignedSatelliteName': self.assigned_satellite_name,  # 任务所属的卫星
            'status': self.status,  # 任务状态
            'clusterName': self.cluster_name,  # 指定任务执行的星簇
            'friendTaskId': self.friend_task_id,  # 合并任务id
            'cloudThickness': self.cloud_thickness or None,  # 云层厚度
            'comment': self.comment  # 备注
        }


class OldTaskModel(db.Model):
    """
    已经完成的任务模型
    """
    __tablename__ = "t_old_task"
    id = db.Column(db.Integer, primary_key=True)  # 主键id
    task_uuid = db.Column(db.String(36), nullable=True, unique=True,
                          default=lambda: str(uuid.uuid4()))  # 稳定业务标识
    task_name = db.Column(db.String(255), nullable=True)  # 任务名
    priority = db.Column(db.Integer, nullable=False)  # 任务的优先级
    is_emergency = db.Column(db.Boolean, default=False)  # 是否是紧急任务
    sensor_type = db.Column(db.String(255), nullable=True)  # 载荷类型
    task_type = db.Column(db.String(255), nullable=False)  # 任务类型
    resolution = db.Column(db.Float, nullable=True)  # 分辨率要求
    start_time = db.Column(db.DateTime)  # 开始时间
    end_time = db.Column(db.DateTime)  # 结束时间
    user_start_time = db.Column(db.DateTime)  # 开始时间
    user_end_time = db.Column(db.DateTime)  # 结束时间
    battery_before = db.Column(db.Text, nullable=True)  # 任务开始前电池电量
    battery_after = db.Column(db.Text, nullable=True)  # 任务结束后电池电量
    storge_before = db.Column(db.Text, nullable=True)  # 任务开始前存储空间
    storge_after = db.Column(db.Text, nullable=True)  # 任务结束后存储空间
    light_power = db.Column(db.String(255), nullable=True)  # 是否有光
    appoint_time = db.Column(db.DateTime, nullable=True)  # 定时时间
    target_location = db.Column(db.String(255), nullable=False)  # 观测位置,[纬度, 经度]
    assigned_satellite_name = db.Column(db.String(255), nullable=True)  # 卫星名  # 任务所属的卫星
    status = db.Column(db.String(255), nullable=False)  # 任务状态,Failed和Success
    friend_task_id = db.Column(db.Integer, nullable=True)  # 合并任务id
    is_photo = db.Column(db.Boolean, default=False)  # 是否已经截图
    path = db.Column(db.Text, nullable=True)  # 图片路径
    height = db.Column(db.Float, nullable=True, default=None)  # 卫星高度
    sub_length = db.Column(db.Integer, nullable=True)  # 子任务数量
    sub_locations = db.Column(db.Text, nullable=True)  # 子任务位置
    cloud_thickness = db.Column(db.Float, nullable=True, default=None)  # 云层厚度
    comment = db.Column(db.Text, nullable=True, default=None)  # 备注
    result_payload = db.Column(db.Text, nullable=True)  # 客户端原始回传
    result_received_at = db.Column(db.DateTime, nullable=True)  # 服务端接收时间

    def to_dict(self):
        """将旧任务模型对象转换为字典"""
        return {
            "id": self.id,  # 任务id
            "taskUuid": self.task_uuid,  # 稳定业务标识
            "taskName": self.task_name,  # 任务名
            "priority": self.priority,  # 任务优先级
            "isEmergency": self.is_emergency,  # 是否是紧急任务
            "sensorType": self.sensor_type,  # 载荷类型
            "taskType": self.task_type,  # 任务类型
            "resolution": self.resolution,  # 分辨率
            "startTime": str(self.start_time) if self.start_time else None,  # 开始时间
            "endTime": str(self.end_time) if self.end_time else None,  # 结束时间
            "targetLocation": self.target_location,  # 目标位置
            "assignedSatelliteName": self.assigned_satellite_name,  # 所属卫星
            "status": self.status,  # 任务状态
            "isPhoto": self.is_photo,  # 是否已经截图
            "path": self.path,  # 图片路径
            "height": self.height,  # 卫星高度
            "subLocations": self.sub_locations,  # 子任务位置
            'cloudThickness': self.cloud_thickness or None,  # 云层厚度
            "comment": self.comment,  # 备注
            "resultPayload": self.result_payload,
            "resultReceivedAt": str(self.result_received_at) if self.result_received_at else None
        }


class TaskResultModel(db.Model):
    """客户端结果收件记录，以稳定业务 UUID 幂等去重。"""
    __tablename__ = "t_task_result"
    task_uuid = db.Column(db.String(36), primary_key=True)
    task_id = db.Column(db.Integer, nullable=True, index=True)
    status = db.Column(db.String(32), nullable=False)
    result_payload = db.Column(db.Text, nullable=False)
    execution_duration_ms = db.Column(db.Integer, nullable=True)
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
