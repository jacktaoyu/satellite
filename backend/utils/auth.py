from functools import wraps

from flask import g, jsonify

from model.UserModel import UserModel


def require_admin(view):
    """要求当前已登录用户为管理员；角色数据异常时按无权限处理。"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        username = getattr(g, 'username', None)
        user = UserModel.query.filter_by(name=username).first() if username else None
        try:
            user_type = int(user.user_type or 0) if user else 0
        except (TypeError, ValueError):
            user_type = 0
        if not user or user_type != 1:
            return jsonify({"meta": {"status": 403, "message": "无权限执行该操作，仅管理员可用"}}), 403
        return view(*args, **kwargs)

    return wrapped
