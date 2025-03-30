# stepflow/application/workflow_execution_service.py

import uuid
from datetime import datetime
from typing import Optional, List
from stepflow.infrastructure.models import WorkflowExecution
from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository

class WorkflowExecutionService:
    def __init__(self, repo: WorkflowExecutionRepository):
        self.repo = repo

    async def start_workflow(self, workflow_id: str, shard_id: int, workflow_type: str) -> WorkflowExecution:
        """
        启动一个新的工作流执行, 并返回该记录
        """
        run_id = str(uuid.uuid4())
        wf_exec = WorkflowExecution(
            run_id=run_id,
            workflow_id=workflow_id,
            shard_id=shard_id,
            status="running",
            workflow_type=workflow_type,
            start_time=datetime.now(),
        )
        return await self.repo.create(wf_exec)

    async def get_execution(self, run_id: str) -> Optional[WorkflowExecution]:
        return await self.repo.get_by_run_id(run_id)

    async def complete_workflow(self, run_id: str, result: str = None) -> bool:
        """
        将工作流置为 'completed' 状态，并设置 close_time, result
        """
        wf_exec = await self.repo.get_by_run_id(run_id)
        if not wf_exec:
            return False
        wf_exec.status = "completed"
        if result:
            wf_exec.result = result
        wf_exec.close_time = datetime.now()
        await self.repo.update(wf_exec)
        return True

    async def fail_workflow(self, run_id: str, result: str = None) -> bool:
        wf_exec = await self.repo.get_by_run_id(run_id)
        if not wf_exec:
            return False
        wf_exec.status = "failed"
        if result:
            wf_exec.result = result
        wf_exec.close_time = datetime.now()
        await self.repo.update(wf_exec)
        return True

    async def delete_workflow(self, run_id: str) -> bool:
        return await self.repo.delete(run_id)

    async def list_workflows(self) -> List[WorkflowExecution]:
        return await self.repo.list_all()

    async def list_by_status(self, status: str) -> List[WorkflowExecution]:
        return await self.repo.list_by_status(status)