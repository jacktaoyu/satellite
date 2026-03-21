from database import db


class UserModel(db.Model):
    """
    用户模型
    """
    __tablename__ = "t_user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键id,自增
    name = db.Column(db.String(255), nullable=False)  # 用户名
    password = db.Column(db.String(255), nullable=False)  # 密码
