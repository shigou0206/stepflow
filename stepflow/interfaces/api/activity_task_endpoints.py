from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from stepflow.persistence.database import get_db_session
from stepflow.service.activity_task_service import ActivityTaskService
from stepflow.persistence.repositories.activity_task_repository import ActivityTaskRepository

router = APIRouter(
    prefix="/activity_tasks",
    tags=["activity_tasks"],
)

# 活动任务响应模型
class ActivityTaskResponse(BaseModel):
    task_token: str
    run_id: str
    activity_type: str
    status: str
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None  # 确保包含错误字段
    error_details: Optional[str] = None  # 确保包含错误详情字段

@router.get("/{task_token}", response_model=ActivityTaskResponse)
async def get_activity_task(task_token: str, db: AsyncSession = Depends(get_db_session)):
    """获取活动任务详情"""
    service = ActivityTaskService(ActivityTaskRepository(db))
    task = await service.get_task(task_token)
    if not task:
        raise HTTPException(status_code=404, detail=f"Activity task with token {task_token} not found")
    return task

@router.get("/run/{run_id}", response_model=List[ActivityTaskResponse])
async def get_tasks_by_run_id(run_id: str, db: AsyncSession = Depends(get_db_session)):
    """获取工作流执行的所有活动任务"""
    service = ActivityTaskService(ActivityTaskRepository(db))
    tasks = await service.get_tasks_by_run_id(run_id)
    return tasks 