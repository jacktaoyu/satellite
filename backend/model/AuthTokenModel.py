from datetime import datetime

from database import db


class AuthTokenModel(db.Model):
    """
    登录令牌表：token 落库持久化，后端重启后已签发的 token 仍然有效
    （原先仅保存在内存字典中，重启即全员掉线）。
    """
    __tablename__ = "t_auth_token"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)  # 令牌串
    username = db.Column(db.String(255), nullable=False, index=True)  # 所属用户名
    expiry = db.Column(db.DateTime, nullable=False)  # 过期时间（naive，本地时间，与既有 VALID_TOKENS 语义一致）
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
