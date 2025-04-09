from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.infrastructure.database import get_db_session
from stepflow.infrastructure.models import ActivityTask
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.application.activity_task_service import ActivityTaskService
from stepflow.interfaces.api.schemas import (
    ActivityTaskResponse,
    CompleteRequest,
    FailRequest,
    HeartbeatRequest
)

router = APIRouter(
    prefix="/activity_tasks",
    tags=["activity_tasks"]
)

# 用于返回给前端的简化模型
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
    """列出所有活动任务"""
    repo = ActivityTaskRepository(db)
    tasks = await repo.list_all()
    return tasks

@router.get("/{task_token}", response_model=ActivityTaskDTO)
async def get_task(task_token: str, db=Depends(get_db_session)):
    """
    获取单个 Task 的详情
    """
    repo = ActivityTaskRepository(db)
    task = await repo.get_by_task_token(task_token)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/run/{run_id}", response_model=List[ActivityTaskResponse])
async def get_tasks_by_run_id(
    run_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取特定工作流执行的活动任务
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    tasks = await svc.get_tasks_by_run_id(run_id)
    return tasks

@router.post("/{task_token}/start")
async def start_task(task_token: str, db=Depends(get_db_session)):
    """
    开始一个活动任务
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.start_task(task_token)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or cannot start")
    return {"status": "ok", "message": f"Task {task_token} started"}

@router.post("/{task_token}/complete")
async def complete_task(task_token: str, req: CompleteRequest, db=Depends(get_db_session)):
    """
    完成一个活动任务，提供结果数据
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.complete_task(task_token, req.result_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or cannot complete")
    
    # 推进工作流执行
    from stepflow.domain.engine.execution_engine import advance_workflow
    await advance_workflow(db, task.run_id)
    
    return {"status": "ok", "message": f"Task {task_token} completed"}

@router.post("/{task_token}/fail")
async def fail_task(task_token: str, req: FailRequest, db=Depends(get_db_session)):
    """
    标记一个活动任务为失败
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.fail_task(task_token, req.reason, req.details)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or cannot fail")
    
    # 更新工作流执行状态为失败
    from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository
    exec_repo = WorkflowExecutionRepository(db)
    wf_exec = await exec_repo.get_by_run_id(task.run_id)
    if wf_exec:
        wf_exec.status = "failed"
        wf_exec.result = f"Activity task failed: {req.reason}"
        await exec_repo.update(wf_exec)
    
    return {"status": "ok", "message": f"Task {task_token} failed"}

@router.post("/{task_token}/heartbeat")
async def heartbeat_task(task_token: str, req: HeartbeatRequest, db=Depends(get_db_session)):
    """
    发送活动任务心跳
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    task = await svc.heartbeat_task(task_token, req.details if hasattr(req, 'details') else None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok", "message": f"Heartbeat received for task {task_token}"}

@router.delete("/{task_token}")
async def delete_task(task_token: str, db=Depends(get_db_session)):
    """
    删除该 Task 记录 (调试用途).
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    ok = await svc.delete_task(task_token)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found or cannot delete")
    return {"status":"ok","message":"Task deleted"}