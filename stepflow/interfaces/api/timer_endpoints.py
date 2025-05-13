from __future__ import annotations

"""FastAPI router for timer management (v2)."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.database import get_db_session
from stepflow.persistence.repositories.timer_repository import TimerRepository
from stepflow.service.timer_service import TimerService
from stepflow.persistence.models import Timer  # only for ORM query fallback

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/timers",
    tags=["Timers"],
    responses={404: {"description": "Timer not found"}},
)

# ---------------------------------------------------------------------------
# Pydantic DTOs
# ---------------------------------------------------------------------------


class TimerDTO(BaseModel):
    timer_id: str
    run_id: str
    state_name: str
    shard_id: int
    fire_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleTimerRequest(BaseModel):
    run_id: str
    state_name: str
    shard_id: int
    fire_at: datetime


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_timer_service(
    db: AsyncSession = Depends(get_db_session),
) -> TimerService:  # pragma: no cover – simple provider
    """Provide TimerService per‑request via FastAPI dependency injection."""
    return TimerService(TimerRepository(db))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=TimerDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a new timer (idempotent)",
)
async def schedule_timer(
    req: ScheduleTimerRequest,
    svc: TimerService = Depends(get_timer_service),
):
    timer = await svc.schedule_timer(
        run_id=req.run_id,
        state_name=req.state_name,
        shard_id=req.shard_id,
        fire_at=req.fire_at,
    )
    return timer


@router.get(
    "/",
    response_model=List[TimerDTO],
    summary="List all timers (paginated)",
)
async def list_all_timers(
    limit: int = Query(100, gt=0, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        Timer.__table__.select()  # type: ignore[attr-defined]
        .order_by(Timer.fire_at.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return result.fetchall()


@router.get(
    "/run/{run_id}",
    response_model=List[TimerDTO],
    summary="List timers for a given workflow run",
)
async def list_timers_for_run(
    run_id: str,
    svc: TimerService = Depends(get_timer_service),
):
    return await svc.timers_for_run(run_id)


@router.get(
    "/{timer_id}",
    response_model=TimerDTO,
    summary="Get single timer by ID",
)
async def get_timer(
    timer_id: str,
    svc: TimerService = Depends(get_timer_service),
):
    timer = await svc.repo.get_by_id(timer_id)
    if not timer:
        raise HTTPException(status_code=404, detail="Timer not found")
    return timer


@router.post(
    "/{timer_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a scheduled timer",
)
async def cancel_timer(
    timer_id: str,
    svc: TimerService = Depends(get_timer_service),
):
    if not await svc.cancel_timer(timer_id):
        raise HTTPException(status_code=400, detail="Cannot cancel timer")
    return {"status": "ok", "message": f"Timer {timer_id} canceled"}


@router.post(
    "/{timer_id}/fire",
    status_code=status.HTTP_200_OK,
    summary="Force‑fire a timer (admin/debug)",
)
async def fire_timer(
    timer_id: str,
    svc: TimerService = Depends(get_timer_service),
):
    if not await svc.fire_timer(timer_id):
        raise HTTPException(status_code=400, detail="Cannot fire timer")
    return {"status": "ok", "message": f"Timer {timer_id} fired"}


@router.delete(
    "/{timer_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a timer (physical delete)",
)
async def delete_timer(
    timer_id: str,
    svc: TimerService = Depends(get_timer_service),
):
    if not await svc.delete_timer(timer_id):
        raise HTTPException(status_code=404, detail="Timer not found or cannot delete")
    return {"status": "ok", "message": f"Timer {timer_id} deleted"}
