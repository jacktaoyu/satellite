from database import db


class UserModel(db.Model):
    """
    用户模型
    """
    __tablename__ = "t_user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键id,自增
    name = db.Column(db.String(255), nullable=False)  # 用户名
    password = db.Column(db.String(255), nullable=False)  # 密码
    user_type = db.Column(db.String(10), nullable=False, default="1")  # 用户类型：1=管理员，其他值（如"0"）均为普通用户
