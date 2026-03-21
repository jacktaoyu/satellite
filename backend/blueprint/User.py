"""
用户类
"""
from flask import Blueprint
from model.UserModel import UserModel

# 创建用户蓝图对象
user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/login', methods=['POST'])
def login():
    pass


@user_bp.route('/<int:user_id>', methods=['PUT'])
def update(self):
    return "修改用户信息"
