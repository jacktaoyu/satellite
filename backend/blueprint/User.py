"""
用户蓝图（当前登录/注册逻辑在 app.py 中直接实现，本蓝图保留供后续扩展）
"""
from flask import Blueprint

user_bp = Blueprint('user', __name__, url_prefix='/user')
