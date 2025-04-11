from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.infrastructure.database import get_db_session
from stepflow.infrastructure.models import WorkflowExecution, ActivityTask
from stepflow.application.workflow_execution_service import WorkflowExecutionService
from stepflow.application.workflow_template_service import WorkflowTemplateService
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.domain.engine.execution_engine import advance_workflow

router = APIRouter(prefix="/workflow_executions", tags=["workflow_executions"])

class StartExecutionRequest(BaseModel):
    template_id: str
    workflow_id: Optional[str] = None
    input: Optional[Dict[str, Any]] = None

class ExecutionResponse(BaseModel):
    run_id: str
    workflow_id: str
    template_id: str
    status: str
    start_time: datetime
    close_time: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

@router.post("/")
async def start_workflow(req: StartExecutionRequest, db: Session = Depends(get_db_session)):
    """
    启动一个新的工作流执行 (异步)
    """
    repo = WorkflowExecutionRepository(db)
    service = WorkflowExecutionService(repo)

    # 1) await 调用 service.start_workflow
    wf_exec = await service.start_workflow(
        template_id=req.template_id,
        workflow_id=req.workflow_id,
        initial_input=req.input or {}
    )

    # 2) 如果 advance_workflow 也是异步，就 await
    await advance_workflow(db, wf_exec.run_id)

    return {
        "status": "ok",
        "run_id": wf_exec.run_id,
        "message": f"Workflow {wf_exec.run_id} started"
    }

@router.get("/{run_id}")
async def get_execution(run_id: str, db: Session = Depends(get_db_session)):
    repo = WorkflowExecutionRepository(db)
    service = WorkflowExecutionService(repo)
    wf = await service.get_execution(run_id)
    if not wf:
        return {"error": "Not found"}

    return {
        "run_id": wf.run_id,
        "workflow_id": wf.workflow_id,
        "template_id": wf.template_id,
        "status": wf.status,
        "workflow_type": wf.workflow_type,
        "start_time": wf.start_time,
        "close_time": wf.close_time,
        "memo": wf.memo,
    }

@router.get("/{run_id}/tasks", response_model=List[Dict[str, Any]])
async def get_workflow_execution_tasks(run_id: str, db: AsyncSession = Depends(get_db_session)):
    """获取工作流执行的所有活动任务"""
    # 查询活动任务
    stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    
    # 转换为响应格式
    response = []
    for task in tasks:
        task_data = {
            "task_token": task.task_token,
            "run_id": task.run_id,
            "activity_type": task.activity_type,
            "status": task.status,
            "scheduled_at": task.scheduled_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }
        
        # 添加输入（如果有）
        if task.input:
            task_data["input"] = task.input
        
        # 添加结果（如果有）
        if task.result:
            task_data["result"] = task.result
        
        # 添加错误信息（如果有）
        if task.error:
            task_data["error"] = task.error
        
        # 添加错误详情（如果有）
        if task.error_details:
            task_data["error_details"] = task.error_details
        
        response.append(task_data)
    
    return response

@router.delete("/{run_id}")
async def cancel_workflow(run_id: str, db: Session = Depends(get_db_session)):
    wf = db.query(WorkflowExecution).filter_by(run_id=run_id).one_or_none()
    if not wf:
        return {"error": "Not found"}
    if wf.status not in ["running"]:
        return {"error": f"Cannot cancel, current status={wf.status}"}

    wf.status = "canceled"
    wf.close_time = datetime.utcnow()
    db.commit()
    return {"status": "ok", "message": f"Workflow {run_id} canceled"}