import uuid
import json
import logging
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any
from sqlalchemy import update

from stepflow.persistence.models import WorkflowExecution
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.interfaces.websocket.connection_manager import manager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WorkflowExecutionService:
    def __init__(self, repo: WorkflowExecutionRepository):
        self.repo = repo

    async def start_workflow(
        self,
        template_id: str,
        workflow_id: Optional[str] = None,
        shard_id: int = 1,
        workflow_type: str = "DefaultFlow",
        initial_input: Optional[Dict[str, Any]] = None,
        mode: str = "inline"
    ) -> WorkflowExecution:
        run_id = str(uuid.uuid4())
        workflow_id = workflow_id or f"wf-{uuid.uuid4()}"
        input_str = json.dumps(initial_input, ensure_ascii=False) if initial_input else None

        wf_exec = WorkflowExecution(
            run_id=run_id,
            template_id=template_id,
            workflow_id=workflow_id,
            shard_id=shard_id,
            mode=mode,
            status="running",
            workflow_type=workflow_type,
            input=input_str,
            start_time=datetime.now(UTC)
        )
        logger.info(f"[start_workflow] Creating workflow {run_id} with template {template_id}")
        return await self.repo.create(wf_exec)

    async def get_execution(self, run_id: str) -> Optional[WorkflowExecution]:
        logger.info(f"[get_execution] Fetching execution for run_id={run_id}")
        return await self.repo.get_by_run_id(run_id)

    async def complete_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        logger.info(f"[complete_workflow] Marking workflow {run_id} as completed")
        return await self._mark_final_state(run_id, "completed", result)

    async def fail_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        logger.info(f"[fail_workflow] Marking workflow {run_id} as failed")
        return await self._mark_final_state(run_id, "failed", result)

    async def cancel_workflow(self, run_id: str, result: Optional[Dict[str, Any]] = None) -> bool:
        logger.info(f"[cancel_workflow] Marking workflow {run_id} as canceled")
        return await self._mark_final_state(run_id, "canceled", result)

    async def _mark_final_state(self, run_id: str, status: str, result: Optional[Dict[str, Any]]) -> bool:
        logger.info(f"[_mark_final_state] Updating status of {run_id} to {status}")
        exec_ = await self.repo.get_by_run_id(run_id)
        if not exec_:
            logger.warning(f"[_mark_final_state] Workflow {run_id} not found")
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

    async def update_status(
        self,
        run_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowExecution]:
        logger.info(f"[update_status] Updating status of {run_id} to {status}")
        exec_ = await self.repo.get_by_run_id(run_id)
        if not exec_:
            logger.warning(f"[update_status] Workflow {run_id} not found")
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

    async def update_current_state(self, run_id: str, current_state_name: str) -> bool:
        logger.info(f"[update_current_state] {run_id} → {current_state_name}")
        exec_ = await self.repo.get_by_run_id(run_id)
        if not exec_:
            return False
        exec_.current_state_name = current_state_name
        await self.repo.update(exec_)
        return True

    async def update_context_snapshot(self, run_id: str, context: Dict[str, Any]) -> bool:
        logger.info(f"[update_context_snapshot] Saving context for {run_id}")
        exec_ = await self.repo.get_by_run_id(run_id)
        if not exec_:
            return False
        exec_.context_snapshot = json.dumps(context, ensure_ascii=False)
        await self.repo.update(exec_)
        return True

    async def get_current_state(self, run_id: str) -> Optional[str]:
        exec_ = await self.repo.get_by_run_id(run_id)
        return exec_.current_state_name if exec_ else None

    async def try_advance_state(self, run_id: str, next_state: str, expected_version: int) -> bool:
        logger.info(f"[try_advance_state] Trying to update {run_id} to {next_state} with version={expected_version}")
        return await self.repo.update_state_and_version(run_id, next_state, expected_version)

    async def delete_workflow(self, run_id: str) -> bool:
        logger.info(f"[delete_workflow] Deleting {run_id}")
        return await self.repo.delete(run_id)

    async def list_workflows(self) -> List[WorkflowExecution]:
        return await self.repo.list_all()

    async def list_by_status(self, status: str) -> List[WorkflowExecution]:
        logger.info(f"[list_by_status] status={status}")
        return await self.repo.list_by_status(status)
