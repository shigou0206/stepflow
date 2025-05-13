from __future__ import annotations

"""Timer service layer – high-level business logic (v3).
Fixes SQLite tzinfo issue by normalising *all* datetimes to
**UTC-naive** using `to_utc_naive` utility.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from stepflow.persistence.models import Timer
from stepflow.persistence.repositories.timer_repository import (
    TimerRepository,
    TimerStatus,
)
from stepflow.utils.timefmt import to_utc_naive   # ← NEW

__all__ = ["TimerService"]


class TimerService:
    """Orchestration helpers built on :class:`TimerRepository`."""

    def __init__(self, repo: TimerRepository):
        self.repo = repo

    # ─────────────────────────── CRUD ───────────────────────────────

    async def schedule_timer(
        self,
        *,
        run_id: str,
        state_name: str,
        shard_id: int,
        fire_at: datetime,
    ) -> Timer:
        """Create new timer or return existing (idempotent)."""
        fire_at = to_utc_naive(fire_at)                 # NORMALISE

        existing = await self.repo.get_by_run_id_and_state(run_id, state_name)
        if existing:
            return existing

        timer = Timer(
            timer_id=str(uuid.uuid4()),
            run_id=run_id,
            state_name=state_name,
            shard_id=shard_id,
            fire_at=fire_at,
            status=TimerStatus.SCHEDULED,
        )
        await self.repo.create(timer)
        await self.repo.session.commit()
        return timer

    async def cancel_timer(self, timer_id: str) -> bool:
        timer = await self.repo.get_by_id(timer_id)
        if not timer or timer.status != TimerStatus.SCHEDULED:
            return False
        timer.status = TimerStatus.CANCELED
        await self.repo.update(timer)
        await self.repo.session.commit()
        return True

    async def fire_timer(self, timer_id: str) -> bool:
        timer = await self.repo.get_by_id(timer_id)
        if not timer or timer.status != TimerStatus.SCHEDULED:
            return False
        timer.status = TimerStatus.FIRED
        await self.repo.update(timer)
        await self.repo.session.commit()
        return True

    async def delete_timer(self, timer_id: str) -> bool:
        deleted = await self.repo.delete(timer_id)
        if deleted:
            await self.repo.session.commit()
        return deleted

    # ─────────────────────────── queries ────────────────────────────

    async def timers_for_run(self, run_id: str) -> List[Timer]:
        return await self.repo.list_by_run_id(run_id)

    async def find_due_timers(
        self,
        *,
        cutoff: datetime,
        limit: int = 100,
        shard_id: int | None = None,
    ) -> List[Timer]:
        return await self.repo.list_scheduled_before(
            cutoff_time=to_utc_naive(cutoff),         # NORMALISE
            limit=limit,
            shard_id=shard_id,
        )

    # ───────────────────── compatibility shim ──────────────────────

    async def get_by_run_id_and_state(self, run_id: str, state_name: str) -> Optional[Timer]:
        return await self.repo.get_by_run_id_and_state(run_id, state_name)

    # ───────────────────────── concurrency ──────────────────────────

    async def try_fire_and_lock(self, timer: Timer, *, now: datetime) -> bool:
        return await self.repo.mark_fired_if_due(timer.timer_id, to_utc_naive(now))