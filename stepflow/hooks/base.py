
from abc import ABC, abstractmethod
from typing import Optional
from stepflow.events.workflow_control import WorkflowControlType


class ExecutionHooks(ABC):

    @abstractmethod
    async def on_workflow_start(self, run_id: str): ...

    @abstractmethod
    async def on_node_enter(self, run_id: str, state_id: str, input: dict): ...

    @abstractmethod
    async def on_node_success(self, run_id: str, state_id: str, output: dict): ...

    @abstractmethod
    async def on_node_fail(self, run_id: str, state_id: str, error: str): ...

    @abstractmethod
    async def on_workflow_end(self, run_id: str, status: str): ...

    @abstractmethod
    async def on_control_signal(self, run_id: str, signal: WorkflowControlType, reason: Optional[str] = None): ...
