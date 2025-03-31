from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
import uuid

from stepflow.infrastructure.database import get_db_session
from stepflow.infrastructure.models import Timer
from stepflow.infrastructure.repositories.timer_repository import TimerRepository
from stepflow.application.timer_service import TimerService
from pydantic import BaseModel

router = APIRouter(prefix="/timers", tags=["timers"])

class TimerDTO(BaseModel):
    timer_id: str
    run_id: str
    shard_id: int
    fire_at: datetime
    status: str

    class Config:
        orm_mode = True

class ScheduleTimerRequest(BaseModel):
    run_id: str
    shard_id: int
    fire_at: datetime

@router.post("/", response_model=TimerDTO)
async def schedule_timer(req: ScheduleTimerRequest, db=Depends(get_db_session)):
    """
    创建一个定时器 (scheduled)
    """
    repo = TimerRepository(db)
    svc = TimerService(repo)
    t = await svc.schedule_timer(
        run_id=req.run_id,
        shard_id=req.shard_id,
        fire_at=req.fire_at
    )
    return t

@router.get("/", response_model=List[TimerDTO])
async def list_all_timers(db=Depends(get_db_session)):
    """
    列出所有定时器 (仅测试/调试用途).
    """
    repo = TimerRepository(db)
    all_timers = db.query(Timer).all()  # or if you have async method: await repo.list_all()
    return all_timers

@router.get("/run/{run_id}", response_model=List[TimerDTO])
async def list_timers_for_run(run_id: str, db=Depends(get_db_session)):
    """
    列出某个 workflow_executions 对应的全部定时器
    """
    repo = TimerRepository(db)
    svc = TimerService(repo)
    timers = await svc.list_timers_for_run(run_id)
    return timers

@router.get("/{timer_id}", response_model=TimerDTO)
async def get_timer(timer_id: str, db=Depends(get_db_session)):
    """
    查看单个定时器详情
    """
    repo = TimerRepository(db)
    t = await repo.get_by_id(timer_id)
    if not t:
        raise HTTPException(status_code=404, detail="Timer not found")
    return t

@router.post("/{timer_id}/cancel")
async def cancel_timer(timer_id: str, db=Depends(get_db_session)):
    """
    取消一个还未触发的定时器
    """
    repo = TimerRepository(db)
    svc = TimerService(repo)
    ok = await svc.cancel_timer(timer_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot cancel timer.")
    return {"status":"ok","message":f"Timer {timer_id} canceled"}

@router.post("/{timer_id}/fire")
async def fire_timer(timer_id: str, db=Depends(get_db_session)):
    """
    手动标记定时器为 fired, 用于测试
    (实际需后续 Engine 处理, e.g. advance_workflow)
    """
    repo = TimerRepository(db)
    svc = TimerService(repo)
    ok = await svc.fire_timer(timer_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot fire timer.")
    # 可能这里要再调用: advance_workflow(run_id) -> ...
    return {"status":"ok","message":f"Timer {timer_id} fired"}

@router.delete("/{timer_id}")
async def delete_timer(timer_id: str, db=Depends(get_db_session)):
    """
    物理删除定时器(测试用途)
    """
    repo = TimerRepository(db)
    svc = TimerService(repo)
    ok = await svc.delete_timer(timer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Timer not found or cannot delete")
    return {"status":"ok","message":f"Timer {timer_id} deleted"}