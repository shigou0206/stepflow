from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from stepflow.infrastructure.database import get_db_session
from stepflow.infrastructure.models import WorkflowVisibility
from stepflow.infrastructure.repositories.workflow_visibility_repository import WorkflowVisibilityRepository
from stepflow.application.workflow_visibility_service import WorkflowVisibilityService

router = APIRouter(prefix="/visibility", tags=["workflow_visibility"])

class VisibilityDTO(BaseModel):
    run_id: str
    workflow_id: Optional[str]
    workflow_type: Optional[str]
    start_time: Optional[datetime]
    close_time: Optional[datetime]
    status: Optional[str]
    memo: Optional[str]
    search_attrs: Optional[str]
    version: Optional[int]

    class Config:
        orm_mode = True

class CreateVisibilityRequest(BaseModel):
    run_id: str
    workflow_id: str
    workflow_type: str
    status: str
    memo: Optional[str] = None
    search_attrs: Optional[str] = None

@router.post("/", response_model=VisibilityDTO)
async def create_visibility(req: CreateVisibilityRequest, db=Depends(get_db_session)):
    """
    创建一条可见性记录
    """
    repo = WorkflowVisibilityRepository(db)
    svc = WorkflowVisibilityService(repo)
    vis = await svc.create_visibility(
        run_id=req.run_id,
        workflow_id=req.workflow_id,
        workflow_type=req.workflow_type,
        status=req.status,
        memo=req.memo,
        search_attrs=req.search_attrs
    )
    return vis

@router.get("/", response_model=List[VisibilityDTO])
async def list_all_visibility(db=Depends(get_db_session)):
    """
    列出所有可见性记录(仅测试/调试用).
    """
    repo = WorkflowVisibilityRepository(db)
    all_vis = await repo.list_all()
    return all_vis

@router.get("/status/{status}", response_model=List[VisibilityDTO])
async def list_visibility_by_status(status: str, db=Depends(get_db_session)):
    """
    按工作流状态查询, 例如 'running', 'completed'...
    """
    repo = WorkflowVisibilityRepository(db)
    svc = WorkflowVisibilityService(repo)
    results = await svc.list_vis_by_status(status)
    return results

@router.get("/{run_id}", response_model=VisibilityDTO)
async def get_visibility(run_id: str, db=Depends(get_db_session)):
    """
    根据 run_id 获取可见性记录
    """
    repo = WorkflowVisibilityRepository(db)
    svc = WorkflowVisibilityService(repo)
    vis = await svc.get_visibility(run_id)
    if not vis:
        raise HTTPException(status_code=404, detail="Visibility not found")
    return vis

class UpdateStatusRequest(BaseModel):
    new_status: str

@router.post("/{run_id}/update_status")
async def update_visibility_status(run_id: str, req: UpdateStatusRequest, db=Depends(get_db_session)):
    """
    更新可见性记录的状态. 如果是 completed/failed/canceled, 会设置 close_time
    """
    repo = WorkflowVisibilityRepository(db)
    svc = WorkflowVisibilityService(repo)
    ok = await svc.update_visibility_status(run_id, req.new_status)
    if not ok:
        raise HTTPException(status_code=404, detail="Visibility not found or update failed")
    return {"status":"ok","message":f"Visibility {run_id} updated to {req.new_status}"}

@router.delete("/{run_id}")
async def delete_visibility(run_id: str, db=Depends(get_db_session)):
    """
    删除可见性记录
    """
    repo = WorkflowVisibilityRepository(db)
    svc = WorkflowVisibilityService(repo)
    deleted = await svc.delete_visibility(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found or cannot delete")
    return {"status":"ok","message":f"Visibility of run_id={run_id} deleted"}