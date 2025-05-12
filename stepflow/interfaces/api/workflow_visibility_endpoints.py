from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.database import get_db_session
from stepflow.persistence.repositories.workflow_visibility_repository import WorkflowVisibilityRepository
from stepflow.service.workflow_visibility_service import WorkflowVisibilityService
from stepflow.interfaces.api.schemas import WorkflowVisibilityResponse
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/workflow_visibility", tags=["workflow_visibility"])

# ----------- 通用返回结构封装 -----------

def standard_response(
    status: str = "ok",
    data: Optional[Any] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    return {"status": status, "data": data, "message": message}

# ----------- API 接口定义 -----------

@router.get("/{run_id}", response_model=Dict[str, Any])
async def get_workflow_visibility(
    run_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取工作流可见性信息。不存在则从 WorkflowExecution 衍生生成。
    """
    repo = WorkflowVisibilityRepository(db)
    service = WorkflowVisibilityService(repo)

    visibility = await service.get_visibility(run_id)

    if not visibility:
        # fallback: 从 WorkflowExecution 派生
        from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
        from stepflow.persistence.models import WorkflowVisibility

        exec_repo = WorkflowExecutionRepository(db)
        execution = await exec_repo.get_by_run_id(run_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Workflow not found")

        visibility = WorkflowVisibility(
            run_id=execution.run_id,
            workflow_id=execution.workflow_id,
            workflow_type=execution.workflow_type,
            start_time=execution.start_time,
            close_time=execution.close_time,
            status=execution.status,
            memo=execution.memo,
            search_attrs=execution.search_attrs,
        )
        await repo.create(visibility)

    return standard_response(data=WorkflowVisibilityResponse.model_validate(visibility))


@router.get("/", response_model=Dict[str, Any])
async def list_workflow_visibility(
    status: Optional[str] = None,
    workflow_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    """
    查询工作流可见性信息，可选过滤（status、workflow_type）
    """
    repo = WorkflowVisibilityRepository(db)
    service = WorkflowVisibilityService(repo)

    if status:
        visibilities = await service.list_by_status(status)
    elif workflow_type:
        visibilities = await service.list_by_workflow_type(workflow_type)
    else:
        visibilities = await service.list_all()

    result = visibilities[skip : skip + limit]
    return standard_response(data=[WorkflowVisibilityResponse.model_validate(v) for v in result])