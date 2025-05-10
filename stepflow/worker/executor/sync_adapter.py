from typing import Dict, Any
from stepflow.dsl.dsl_model import TaskState
from stepflow.worker.task_executor import TaskExecutor
from stepflow.worker.executor.interfaces import ITaskExecutor


class SyncExecutorAdapter(ITaskExecutor):
    """
    默认的同步执行器实现，直接执行任务并返回结果。
    用于与现有 TaskExecutor 兼容。
    """
    def __init__(self):
        self.executor = TaskExecutor()

    async def submit_task(self, state: TaskState, input_data: Dict[str, Any]) -> str:
        """
        对于同步执行器，不需要实际生成任务 ID，因此返回固定字符串。
        """
        self._last_output = await self.executor.run_task(state, input_data)
        return "sync-task"

    async def poll_result(self, task_token: str) -> Dict[str, Any]:
        """
        直接返回上次执行结果。
        """
        return self._last_output