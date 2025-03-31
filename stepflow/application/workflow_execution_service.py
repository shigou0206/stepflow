# stepflow/application/workflow_execution_service.py

import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict
from stepflow.infrastructure.models import WorkflowExecution
from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository

class WorkflowExecutionService:
    def __init__(self, repo: WorkflowExecutionRepository):
        self.repo = repo

    async def start_workflow(
        self,
        template_id: str,
        workflow_id: Optional[str] = None,
        shard_id: int = 1,
        workflow_type: str = "DefaultFlow",
        initial_input: Optional[Dict] = None
    ) -> WorkflowExecution:
        """
        启动一个新的工作流执行, 并返回该记录
        """
        run_id = str(uuid.uuid4())

        if not workflow_id:
            workflow_id = f"wf-{uuid.uuid4()}"  # 或自行指定

        # 如果 initial_input 是 dict，就转成 JSON字符串以存储
        input_str = json.dumps(initial_input) if initial_input else None

        wf_exec = WorkflowExecution(
            run_id=run_id,
            template_id=template_id,       # 新增: 记录用哪个模板
            workflow_id=workflow_id,
            shard_id=shard_id,
            status="running",
            workflow_type=workflow_type,
            input=input_str,               # 存储启动数据
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