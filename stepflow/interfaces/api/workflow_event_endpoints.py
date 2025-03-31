from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime

from stepflow.infrastructure.database import get_db_session
from stepflow.infrastructure.models import WorkflowEvent
from stepflow.infrastructure.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.application.workflow_event_service import WorkflowEventService
from pydantic import BaseModel

router = APIRouter(prefix="/workflow_events", tags=["workflow_events"])

class WorkflowEventDTO(BaseModel):
    id: int
    run_id: str
    shard_id: int
    event_id: int
    event_type: str
    attributes: str
    archived: bool
    timestamp: datetime

    class Config:
        orm_mode = True

@router.get("/", response_model=List[WorkflowEventDTO])
async def list_all_events(db=Depends(get_db_session)):
    """
    列出所有事件(仅测试/调试用途).
    生产中可加过滤/分页.
    """
    repo = WorkflowEventRepository(db)
    # 需要你的 repo 有 list_all() 之类异步方法
    # 若无可先 .all()
    # 这里为简化，假设 synchronous
    events = db.query(WorkflowEvent).order_by(WorkflowEvent.id.asc()).all()
    return events

@router.get("/run/{run_id}", response_model=List[WorkflowEventDTO])
async def list_events_for_run(run_id: str, db=Depends(get_db_session)):
    """
    列出指定 run_id 的全部事件
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    evts = await svc.list_events_for_run(run_id)
    return evts

@router.get("/{db_id}", response_model=WorkflowEventDTO)
async def get_event(db_id: int, db=Depends(get_db_session)):
    """
    根据DB主键id获取事件
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    evt = await svc.get_event(db_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    return evt

class RecordEventRequest(BaseModel):
    run_id: str
    shard_id: int
    event_id: int
    event_type: str
    attributes: str = "{}"
    archived: bool = False

@router.post("/", response_model=WorkflowEventDTO)
async def record_event(req: RecordEventRequest, db=Depends(get_db_session)):
    """
    仅调试用途: 手动创建一条 WorkflowEvent
    正常应由 Engine/Worker 来自动写入
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    new_evt = await svc.record_event(
        run_id=req.run_id,
        shard_id=req.shard_id,
        event_id=req.event_id,
        event_type=req.event_type,
        attributes=req.attributes,
        archived=req.archived
    )
    return new_evt

@router.post("/{db_id}/archive")
async def archive_event(db_id: int, db=Depends(get_db_session)):
    """
    将某条事件 archived=True
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    ok = await svc.archive_event(db_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or cannot archive")
    return {"status":"ok","message":f"Event {db_id} archived"}

@router.delete("/{db_id}")
async def delete_event(db_id: int, db=Depends(get_db_session)):
    """
    物理删除事件
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    ok = await svc.delete_event(db_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or cannot delete")
    return {"status":"ok","message":f"Event {db_id} deleted"}