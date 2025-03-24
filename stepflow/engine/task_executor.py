# engine/task_executor.py
from abc import ABC, abstractmethod
from stepflow.resources.registry import RESOURCE_REGISTRY

class ITaskExecutor(ABC):
    @abstractmethod
    def execute_task(self, resource_name: str, parameters: dict) -> dict:
        """
        执行给定的 resource + 参数，并返回执行结果(同步).
        """
        pass

class LocalExecutor(ITaskExecutor):
    def execute_task(self, resource_name: str, parameters: dict) -> dict:
        if resource_name not in RESOURCE_REGISTRY:
            raise Exception(f"Unknown resource: {resource_name}")
        func = RESOURCE_REGISTRY[resource_name]
        # 同步调用本地函数
        return func(parameters)