from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.database import get_db_session
from stepflow.persistence.models import WorkflowEvent
from stepflow.persistence.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.service.workflow_event_service import WorkflowEventService

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/workflow_events", tags=["workflow_events"])

# ----------- DTOs & Request Models -----------

class RecordEventRequest(BaseModel):
    run_id: str
    shard_id: int
    event_id: int
    event_type: str
    attributes: str = "{}"
    archived: bool = False

class WorkflowEventDTO(BaseModel):
    id: int
    run_id: str
    shard_id: int
    event_id: int
    event_type: str
    attributes: str
    archived: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------- Helper response wrapper -----------

def standard_response(
    status: str = "ok",
    data: Optional[Any] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    return {
        "status": status,
        "data": data,
        "message": message
    }

# ----------- Endpoints -----------

@router.get("/", response_model=Dict[str, Any])
async def list_all_events(
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(100, le=1000),
    offset: int = Query(0)
):
    """
    列出所有事件（测试用途）。支持分页参数。
    """
    stmt = select(WorkflowEvent).order_by(WorkflowEvent.id.asc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    events = result.scalars().all()
    return standard_response(data=[WorkflowEventDTO.model_validate(e) for e in events])


@router.get("/run/{run_id}", response_model=Dict[str, Any])
async def list_events_for_run(run_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    列出指定 run_id 的全部事件
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    events = await svc.list_events_for_run(run_id)
    return standard_response(data=[WorkflowEventDTO.model_validate(e) for e in events])


@router.get("/{db_id}", response_model=Dict[str, Any])
async def get_event(db_id: int, db: AsyncSession = Depends(get_db_session)):
    """
    根据 DB 主键 id 获取事件
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    evt = await svc.get_event(db_id)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    return standard_response(data=WorkflowEventDTO.model_validate(evt))


@router.post("/", response_model=Dict[str, Any])
async def record_event(req: RecordEventRequest, db: AsyncSession = Depends(get_db_session)):
    """
    手动记录事件（调试用途）
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
    return standard_response(data=WorkflowEventDTO.model_validate(new_evt), message="Event recorded")


@router.post("/{db_id}/archive", response_model=Dict[str, Any])
async def archive_event(db_id: int, db: AsyncSession = Depends(get_db_session)):
    """
    将某条事件标记为 archived=True
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    ok = await svc.archive_event(db_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or cannot archive")
    return standard_response(message=f"Event {db_id} archived")


@router.delete("/{db_id}", response_model=Dict[str, Any])
async def delete_event(db_id: int, db: AsyncSession = Depends(get_db_session)):
    """
    物理删除事件
    """
    repo = WorkflowEventRepository(db)
    svc = WorkflowEventService(repo)
    ok = await svc.delete_event(db_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Event not found or cannot delete")
    return standard_response(message=f"Event {db_id} deleted")