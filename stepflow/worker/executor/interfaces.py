from typing import Dict, Any
from stepflow.dsl.dsl_model import TaskState
from abc import ABC, abstractmethod


class ITaskExecutor(ABC):
    @abstractmethod
    async def submit_task(self, run_id: str, state_name: str, state: TaskState, input_data: Dict[str, Any]) -> bool:
        """提交任务到执行器（同步或异步）"""
        pass

    @abstractmethod
    async def poll_result(self, run_id: str, state_name: str) -> Dict[str, Any]:
        """轮询或等待任务完成结果（可选实现立即返回）"""
        pass
