from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.models import Timer
from stepflow.persistence.repositories.base_repository import BaseRepository


class TimerRepository(BaseRepository[Timer]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Timer)

    def get_id_attribute(self) -> str:  # noqa: D401
        """返回主键属性名称 (`timer_id`)."""
        return "timer_id"

    # ------------------------------------------------------------------ #
    # 📄 自定义查询
    # ------------------------------------------------------------------ #

    async def get_by_run_id_and_state(
        self,
        run_id: str,
        state_name: str,
    ) -> Optional[Timer]:
        """
        根据 `(run_id, state_name)` 获取唯一定时器记录。

        WaitState 在创建或复用定时器时用来判重。
        **注意**：模型 `Timer` 需包含 `state_name` 列并在 DB 建唯一索引 `(run_id, state_name)`.
        """
        stmt = (
            select(Timer)
            .where(
                Timer.run_id == run_id,
                Timer.state_name == state_name,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_scheduled_before(self, cutoff_time: datetime) -> List[Timer]:
        """
        获取 ``status='scheduled'`` 且 ``fire_at`` 不晚于 `cutoff_time`
        的定时器（供调度器批量扫描）。
        """
        stmt = (
            select(Timer)
            .where(
                Timer.status == "scheduled",
                Timer.fire_at <= cutoff_time,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_run_id(self, run_id: str) -> List[Timer]:
        """列出同一个 `run_id` 的全部定时器记录。"""
        stmt = select(Timer).where(Timer.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()