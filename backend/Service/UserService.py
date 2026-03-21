"""
用户类
"""


class User:
    def __init__(self, user_id, name, password):
        """
        初始化用户
        """
        self.user_id = user_id
        self.name = name
        self.password = password
