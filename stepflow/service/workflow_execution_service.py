import uuid
import json
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any
from stepflow.persistence.models import WorkflowExecution
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.interfaces.websocket.connection_manager import manager


class WorkflowExecutionService:
    def __init__(self, repo: WorkflowExecutionRepository):
        self.repo = repo

    async def start_workflow(
        self,
        template_id: str,
        workflow_id: Optional[str] = None,
        shard_id: int = 1,
        workflow_type: str = "DefaultFlow",
        initial_input: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        run_id = str(uuid.uuid4())
        workflow_id = workflow_id or f"wf-{uuid.uuid4()}"
        input_str = json.dumps(initial_input, ensure_ascii=False) if initial_input else None

        wf_exec = WorkflowExecution(
            run_id=run_id,
            template_id=template_id,
            workflow_id=workflow_id,
            shard_id=shard_id,
            status="running",
            workflow_type=workflow_type,
            input=input_str,
            start_time=datetime.now(UTC)
        )
        return await self.repo.create(wf_exec)

    async def get_execution(self, run_id: str) -> Optional[WorkflowExecution]:
        return await self.repo.get_by_run_id(run_id)

    async def complete_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        return await self._mark_final_state(run_id, "completed", result)

    async def fail_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        return await self._mark_final_state(run_id, "failed", result)

    async def cancel_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        return await self._mark_final_state(run_id, "canceled", result)

    async def _mark_final_state(self, run_id: str, status: str, result: Optional[Dict[str, Any]]) -> bool:
        exec_ = await self.repo.get_by_run_id(run_id)
        if not exec_:
            return False
        exec_.status = status
        exec_.close_time = datetime.now(UTC)
        if result:
            exec_.result = json.dumps(result, ensure_ascii=False)
        await self.repo.update(exec_)
        await manager.send_to_workflow(run_id, {
            "type": "status_update",
            "run_id": run_id,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat()
        })
        return True

    async def delete_workflow(self, run_id: str) -> bool:
        return await self.repo.delete(run_id)

    async def list_workflows(self) -> List[WorkflowExecution]:
        return await self.repo.list_all()

    async def list_by_status(self, status: str) -> List[WorkflowExecution]:
        return await self.repo.list_by_status(status)

    async def update_status(
        self,
        run_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowExecution]:
        exec_ = await self.repo.get_by_run_id(run_id)
        if not exec_:
            return None
        exec_.status = status
        if status in {"completed", "failed", "canceled"}:
            exec_.close_time = datetime.now(UTC)
        if result:
            exec_.result = json.dumps(result, ensure_ascii=False)
        updated = await self.repo.update(exec_)
        await manager.send_to_workflow(run_id, {
            "type": "status_update",
            "run_id": run_id,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat()
        })
        return updated