from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.database import get_db_session
from stepflow.persistence.models import Timer
from stepflow.persistence.repositories.timer_repository import TimerRepository
from stepflow.service.timer_service import TimerService

router = APIRouter(prefix="/timers", tags=["timers"])

class TimerDTO(BaseModel):
    timer_id: str
    run_id: str
    shard_id: int
    fire_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)

class ScheduleTimerRequest(BaseModel):
    run_id: str
    shard_id: int
    fire_at: datetime

@router.post("/", response_model=TimerDTO)
async def schedule_timer(req: ScheduleTimerRequest, db: AsyncSession = Depends(get_db_session)):
    repo = TimerRepository(db)
    svc = TimerService(repo)
    t = await svc.schedule_timer(
        run_id=req.run_id,
        shard_id=req.shard_id,
        fire_at=req.fire_at
    )
    return t

@router.get("/", response_model=List[TimerDTO])
async def list_all_timers(db: AsyncSession = Depends(get_db_session)):
    stmt = select(Timer).order_by(Timer.fire_at.asc())
    result = await db.execute(stmt)
    all_timers = result.scalars().all()
    return all_timers

@router.get("/run/{run_id}", response_model=List[TimerDTO])
async def list_timers_for_run(run_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = TimerRepository(db)
    svc = TimerService(repo)
    return await svc.list_timers_for_run(run_id)

@router.get("/{timer_id}", response_model=TimerDTO)
async def get_timer(timer_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = TimerRepository(db)
    t = await repo.get_by_id(timer_id)
    if not t:
        raise HTTPException(status_code=404, detail="Timer not found")
    return t

@router.post("/{timer_id}/cancel")
async def cancel_timer(timer_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = TimerRepository(db)
    svc = TimerService(repo)
    ok = await svc.cancel_timer(timer_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot cancel timer.")
    return {"status": "ok", "message": f"Timer {timer_id} canceled"}

@router.post("/{timer_id}/fire")
async def fire_timer(timer_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = TimerRepository(db)
    svc = TimerService(repo)
    ok = await svc.fire_timer(timer_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Cannot fire timer.")
    return {"status": "ok", "message": f"Timer {timer_id} fired"}

@router.delete("/{timer_id}")
async def delete_timer(timer_id: str, db: AsyncSession = Depends(get_db_session)):
    repo = TimerRepository(db)
    svc = TimerService(repo)
    ok = await svc.delete_timer(timer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Timer not found or cannot delete")
    return {"status": "ok", "message": f"Timer {timer_id} deleted"}