from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.models import Timer
from stepflow.persistence.repositories.base_repository import BaseRepository


class TimerRepository(BaseRepository[Timer]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Timer)

    def get_id_attribute(self) -> str:
        return "timer_id"

    async def get_by_id(self, timer_id: str) -> Optional[Timer]:
        return await super().get_by_id(timer_id)

    async def list_by_run_id(self, run_id: str) -> List[Timer]:
        stmt = select(Timer).where(Timer.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_scheduled_before(self, cutoff_time: datetime) -> List[Timer]:
        stmt = (
            select(Timer)
            .where(Timer.status == "scheduled", Timer.fire_at <= cutoff_time)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()