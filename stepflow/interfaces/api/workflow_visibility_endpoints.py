from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.database import get_db_session
from stepflow.persistence.repositories.workflow_visibility_repository import WorkflowVisibilityRepository
from stepflow.service.workflow_visibility_service import WorkflowVisibilityService
from stepflow.interfaces.api.schemas import WorkflowVisibilityResponse

router = APIRouter(
    prefix="/workflow_visibility",
    tags=["workflow_visibility"],
)

@router.get("/{run_id}", response_model=WorkflowVisibilityResponse)
async def get_workflow_visibility(
    run_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取工作流可见性信息
    """
    repo = WorkflowVisibilityRepository(db)
    service = WorkflowVisibilityService(repo)
    
    visibility = await service.get_visibility(run_id)
    if not visibility:
        # 如果没有找到可见性记录，尝试从工作流执行中获取
        from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
        exec_repo = WorkflowExecutionRepository(db)
        execution = await exec_repo.get_by_run_id(run_id)
        
        if not execution:
            raise HTTPException(status_code=404, detail="Workflow visibility not found")
        
        # 创建可见性记录
        from stepflow.persistence.models import WorkflowVisibility
        visibility = WorkflowVisibility(
            run_id=execution.run_id,
            workflow_id=execution.workflow_id,
            workflow_type=execution.workflow_type,
            start_time=execution.start_time,
            close_time=execution.close_time,
            status=execution.status,
            memo=execution.memo,
            search_attrs=execution.search_attrs
        )
        
        # 保存可见性记录
        await repo.create(visibility)
        
    return visibility

@router.get("/", response_model=List[WorkflowVisibilityResponse])
async def list_workflow_visibility(
    status: Optional[str] = None,
    workflow_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    """
    列出工作流可见性信息
    """
    repo = WorkflowVisibilityRepository(db)
    service = WorkflowVisibilityService(repo)
    
    if status:
        visibilities = await service.list_by_status(status)
    elif workflow_type:
        visibilities = await service.list_by_workflow_type(workflow_type)
    else:
        visibilities = await service.list_all()
    
    return visibilities[skip : skip + limit]