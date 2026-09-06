from database import db


class CaseHistoryModel(db.Model):
    """
    示范用例执行历史模型（替代前端 localStorage 存储，换浏览器不丢失）
    """
    __tablename__ = "t_case_history"
    id = db.Column(db.Integer, primary_key=True)  # 主键id
    case_type = db.Column(db.String(64), nullable=False)  # 用例类型标识：point/area/ocean
    case_name = db.Column(db.String(255), nullable=False)  # 用例名称
    success = db.Column(db.Boolean, default=True)  # 是否成功
    task_count = db.Column(db.Integer, nullable=True)  # 生成任务数
    message = db.Column(db.Text, nullable=True)  # 执行结果描述
    executed_at = db.Column(db.DateTime, nullable=False)  # 执行时间

    def to_dict(self):
        """将用例执行历史对象转换为字典"""
        return {
            'id': self.id,
            'caseType': self.case_type,
            'caseName': self.case_name,
            'success': self.success,
            'taskCount': self.task_count,
            'message': self.message,
            'time': str(self.executed_at) if self.executed_at else None
        }
