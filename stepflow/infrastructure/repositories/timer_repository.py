# stepflow/infrastructure/repositories/timer_repository.py

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from stepflow.infrastructure.models import Timer

class TimerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, timer: Timer) -> Timer:
        """
        插入新的定时器记录并提交
        """
        self.db.add(timer)
        await self.db.commit()
        await self.db.refresh(timer)
        return timer

    async def get_by_id(self, timer_id: str) -> Optional[Timer]:
        """
        通过 timer_id (主键) 获取对应 Timer 记录
        """
        stmt = select(Timer).where(Timer.timer_id == timer_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, timer: Timer) -> Timer:
        """
        外部修改 timer 对象后，调用 update() 进行提交
        """
        await self.db.commit()
        await self.db.refresh(timer)
        return timer

    async def delete(self, timer_id: str) -> bool:
        """
        根据 timer_id 删除对应记录，返回是否删除成功
        """
        t = await self.get_by_id(timer_id)
        if not t:
            return False
        await self.db.delete(t)
        await self.db.commit()
        return True

    async def list_by_run_id(self, run_id: str) -> List[Timer]:
        """
        根据 run_id 列出所有定时器，用于查看某个 workflow 实例下的所有定时器
        """
        stmt = select(Timer).where(Timer.run_id == run_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_scheduled_before(self, cutoff_time) -> List[Timer]:
        """
        列出 fire_at <= cutoff_time 且 status='scheduled' 的所有定时器
        方便实现轮询，找到该触发时刻前需要执行的定时器
        """
        stmt = select(Timer).where(
            Timer.status == "scheduled",
            Timer.fire_at <= cutoff_time
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()