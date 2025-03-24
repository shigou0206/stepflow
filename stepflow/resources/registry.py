# resources/registry.py
RESOURCE_REGISTRY = {}

def resource(name: str):
    """
    装饰器：给函数加上 “@resource('shell.exec')”，
    这样它会自动登记到全局 RESOURCE_REGISTRY[name] = function
    """
    def decorator(fn):
        RESOURCE_REGISTRY[name] = fn
        return fn
    return decorator