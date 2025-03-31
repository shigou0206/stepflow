from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from stepflow.infrastructure.database import get_db_session
from stepflow.infrastructure.models import ActivityTask
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.application.activity_task_service import ActivityTaskService

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
    result: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    heartbeat_at: Optional[datetime]

    class Config:
        orm_mode = True  # 允许直接从 SQLAlchemy model 转

@router.get("/", response_model=List[ActivityTaskDTO])
async def list_all_tasks(db=Depends(get_db_session)):
    """
    列出全部 ActivityTask (仅供调试/测试).
    实际生产中可能要加分页/过滤.
    """
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

@router.get("/run/{run_id}", response_model=List[ActivityTaskDTO])
async def list_tasks_for_run(run_id: str, db=Depends(get_db_session)):
    """
    列出同一工作流里的所有 Task
    """
    repo = ActivityTaskRepository(db)
    tasks = await repo.list_by_run_id(run_id)
    return tasks

class CompleteRequest(BaseModel):
    result_data: str

@router.post("/{task_token}/start")
async def start_task(task_token: str, db=Depends(get_db_session)):
    """
    手动将活动任务从 'scheduled' 改为 'running'
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    ok = await svc.start_task(task_token)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot start task. Maybe not in 'scheduled' state.")
    return {"status":"ok","message":"Task started"}

@router.post("/{task_token}/complete")
async def complete_task(task_token: str, req: CompleteRequest, db=Depends(get_db_session)):
    """
    手动完成任务, 并写入 result
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    ok = await svc.complete_task(task_token, req.result_data)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot complete task. Maybe not in 'running' state.")
    return {"status":"ok","message":"Task completed"}

class FailRequest(BaseModel):
    reason: str

@router.post("/{task_token}/fail")
async def fail_task(task_token: str, req: FailRequest, db=Depends(get_db_session)):
    """
    手动将任务标记为 failed, 并记录失败原因
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    ok = await svc.fail_task(task_token, req.reason)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot fail task.")
    return {"status":"ok","message":"Task failed"}

@router.post("/{task_token}/heartbeat")
async def heartbeat_task(task_token: str, db=Depends(get_db_session)):
    """
    更新 heartbeart, 用于长时间运行或定期告知 Worker 仍在执行
    """
    repo = ActivityTaskRepository(db)
    svc = ActivityTaskService(repo)
    ok = await svc.heartbeat_task(task_token)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot heartbeat. Task not in 'running'?")
    return {"status":"ok","message":"heartbeat updated"}

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