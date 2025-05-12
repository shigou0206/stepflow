from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.database import get_db_session
from stepflow.persistence.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.service.activity_task_service import ActivityTaskService
from stepflow.interfaces.api.schemas import (
    ActivityTaskResponse,
    CompleteRequest,
    FailRequest,
    HeartbeatRequest
)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/activity_tasks",
    tags=["activity_tasks"]
)

class ActivityTaskDTO(BaseModel):
    task_token: str
    run_id: str
    shard_id: int
    seq: int
    activity_type: str
    status: str
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[ActivityTaskResponse])
async def list_all_tasks(db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    return await repo.list_all()

@router.get("/{task_token}", response_model=ActivityTaskDTO)
async def get_task(task_token: str, db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    task = await repo.get_by_task_token(task_token)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/run/{run_id}", response_model=List[ActivityTaskResponse])
async def get_tasks_by_run_id(run_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    return await svc.get_tasks_by_run_id(run_id)

@router.post("/{task_token}/start")
async def start_task(task_token: str, db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.start_task(task_token)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or cannot start")
    return {"status": "ok", "message": f"Task {task_token} started"}

@router.post("/{task_token}/complete")
async def complete_task(task_token: str, req: CompleteRequest, db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.complete_task(task_token, req.result_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or cannot complete")

    # 推进流程（注意：可抽离封装）
    from stepflow.engine.workflow_engine import advance_workflow
    await advance_workflow(task.run_id)

    return {"status": "ok", "message": f"Task {task_token} completed"}

@router.post("/{task_token}/fail")
async def fail_task(task_token: str, req: FailRequest, db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.fail_task(task_token, req.reason, req.details)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or cannot fail")

    # 标记 workflow 失败（可封装进 service）
    from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
    exec_repo = WorkflowExecutionRepository(db)
    wf_exec = await exec_repo.get_by_run_id(task.run_id)
    if wf_exec:
        wf_exec.status = "failed"
        wf_exec.result = f"Activity task failed: {req.reason}"
        await exec_repo.update(wf_exec)

    return {"status": "ok", "message": f"Task {task_token} failed"}

@router.post("/{task_token}/heartbeat")
async def heartbeat_task(task_token: str, req: HeartbeatRequest, db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.heartbeat_task(task_token, getattr(req, 'details', None))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok", "message": f"Heartbeat received for task {task_token}"}

@router.delete("/{task_token}")
async def delete_task(task_token: str, db: AsyncSession = Depends(get_db_session)):
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    ok = await svc.delete_task(task_token)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found or cannot delete")
    return {"status": "ok", "message": "Task deleted"}