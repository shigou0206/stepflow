from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.models import Timer
from stepflow.persistence.repositories.base_repository import BaseRepository
from stepflow.utils.timefmt import to_utc_naive

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TimerStatus:
    SCHEDULED = "scheduled"
    FIRED     = "fired"
    CANCELED  = "canceled"


class TimerRepository(BaseRepository[Timer]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Timer)

    def get_id_attribute(self) -> str:
        return "timer_id"

    async def get_by_run_id_and_state(self, run_id: str, state_name: str) -> Optional[Timer]:
        stmt = (
            select(Timer)
            .where(Timer.run_id == run_id, Timer.state_name == state_name)
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_scheduled_before(
        self,
        cutoff_time: datetime,
        *,
        limit: int = 100,
        shard_id: int | None = None,
    ) -> List[Timer]:
        cutoff_naive = to_utc_naive(cutoff_time)
        conditions = [
            Timer.status == TimerStatus.SCHEDULED,
            Timer.fire_at <= cutoff_naive,
        ]
        if shard_id is not None:
            conditions.append(Timer.shard_id == shard_id)

        stmt = (
            select(Timer)
            .where(*conditions)
            .order_by(Timer.fire_at)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def list_by_run_id(self, run_id: str) -> List[Timer]:
        stmt = select(Timer).where(Timer.run_id == run_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def mark_fired_if_due(self, timer_id: str, now: datetime) -> bool:
        now_naive = to_utc_naive(now)

        logger.debug(
            "[TimerRepo] ⏱ try claim: timer_id=%s fire_at <= now=%s",
            timer_id, now_naive
        )

        stmt = (
            update(Timer)
            .where(
                Timer.timer_id == timer_id,
                Timer.status == TimerStatus.SCHEDULED,
                Timer.fire_at <= now_naive,
            )
            .values(status=TimerStatus.FIRED)
            .execution_options(synchronize_session=False)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        if result.rowcount == 1:
            logger.debug("[TimerRepo] ✅ Claimed timer_id=%s", timer_id)
        else:
            logger.debug("[TimerRepo] 🚫 Not claimed timer_id=%s — maybe already fired or too early", timer_id)

        return result.rowcount == 1