from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from stepflow.persistence.database import get_db_session
from stepflow.persistence.models import WorkflowExecution, ActivityTask
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.service.workflow_execution_service import WorkflowExecutionService
from stepflow.engine.workflow_engine import advance_workflow, run_inline_workflow

router = APIRouter(prefix="/workflow_executions", tags=["workflow_executions"])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------ DTO & Request ------------

class StartExecutionRequest(BaseModel):
    template_id: str
    workflow_id: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    mode: Literal["inline", "deferred"] = "inline"

class ExecutionResponse(BaseModel):
    run_id: str
    workflow_id: str
    template_id: str
    status: str
    start_time: datetime
    close_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ------------ Endpoints ------------

@router.post("/", response_model=Dict[str, Any])
async def start_workflow(req: StartExecutionRequest, db: AsyncSession = Depends(get_db_session)):
    repo = WorkflowExecutionRepository(db)
    service = WorkflowExecutionService(repo)

    wf_exec = await service.start_workflow(
        template_id=req.template_id,
        workflow_id=req.workflow_id,
        initial_input=req.input or {},
        mode=req.mode
    )

    try:
        if req.mode == "deferred":
            await advance_workflow(wf_exec.run_id)
        else:
            await run_inline_workflow(wf_exec.run_id)
    except Exception as e:
        logger.exception(f"[{wf_exec.run_id}] ❌ Failed to start workflow: {e}")
        await service.fail_workflow(wf_exec.run_id, {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {e}")

    return {
        "status": "ok",
        "run_id": wf_exec.run_id,
        "message": f"Workflow {wf_exec.run_id} started"
    }

@router.get("/{run_id}", response_model=Dict[str, Any])
async def get_execution(run_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = WorkflowExecutionRepository(db)
    service = WorkflowExecutionService(repo)
    wf = await service.get_execution(run_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    return {
        "status": "ok",
        "data": {
            "run_id": wf.run_id,
            "workflow_id": wf.workflow_id,
            "template_id": wf.template_id,
            "status": wf.status,
            "workflow_type": wf.workflow_type,
            "start_time": wf.start_time,
            "close_time": wf.close_time,
            "memo": wf.memo,
        }
    }

@router.get("/{run_id}/tasks", response_model=List[Dict[str, Any]])
async def get_workflow_execution_tasks(run_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return [
        {
            "task_token": t.task_token,
            "run_id": t.run_id,
            "activity_type": t.activity_type,
            "status": t.status,
            "scheduled_at": t.scheduled_at,
            "started_at": t.started_at,
            "completed_at": t.completed_at,
            "input": t.input,
            "result": t.result,
            "error": t.error,
            "error_details": t.error_details
        }
        for t in tasks
    ]

@router.delete("/{run_id}", response_model=Dict[str, Any])
async def cancel_workflow(run_id: str, db: AsyncSession = Depends(get_db_session)):
    stmt = select(WorkflowExecution).filter_by(run_id=run_id)
    result = await db.execute(stmt)
    wf = result.scalars().one_or_none()

    if not wf:
        raise HTTPException(status_code=404, detail="Workflow execution not found")

    if wf.status not in ["running"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel, current status={wf.status}")

    wf.status = "canceled"
    wf.close_time = datetime.now(UTC)
    await db.commit()

    return {
        "status": "ok",
        "message": f"Workflow {run_id} canceled"
    }