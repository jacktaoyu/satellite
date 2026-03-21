class OCCProxy:
    """代理类，用于延迟对OCC实例的访问"""

    def __init__(self):
        self._instance = None

    def set_instance(self, instance):
        self._instance = instance

    def __getattr__(self, name):
        if self._instance is None:
            raise RuntimeError("OperationsControlCenter实例尚未初始化")
        return getattr(self._instance, name)
        
    def __setattr__(self, name, value):
        if name == '_instance':
            super().__setattr__(name, value)
        elif self._instance is None:
            raise RuntimeError("OperationsControlCenter实例尚未初始化")
        else:
            setattr(self._instance, name, value)


# 创建全局代理对象
occ = OCCProxy()
