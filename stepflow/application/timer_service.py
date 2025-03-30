# stepflow/application/timer_service.py

import uuid
from datetime import datetime
from typing import Optional, List
from stepflow.infrastructure.models import Timer
from stepflow.infrastructure.repositories.timer_repository import TimerRepository

class TimerService:
    def __init__(self, repo: TimerRepository):
        self.repo = repo

    async def schedule_timer(self, run_id: str, shard_id: int, fire_at: datetime) -> Timer:
        """
        创建一个新的定时器, 初始状态 scheduled
        """
        timer_id = str(uuid.uuid4())
        t = Timer(
            timer_id=timer_id,
            run_id=run_id,
            shard_id=shard_id,
            fire_at=fire_at,
            status="scheduled",
        )
        return await self.repo.create(t)

    async def cancel_timer(self, timer_id: str) -> bool:
        """
        将定时器状态改为 canceled, 或物理删除
        """
        t = await self.repo.get_by_id(timer_id)
        if not t:
            return False
        if t.status != "scheduled":
            return False  # 只能取消还未触发的定时器
        t.status = "canceled"
        await self.repo.update(t)
        return True

    async def fire_timer(self, timer_id: str) -> bool:
        """
        将定时器标记为 fired
        (在外部调用时, 可能还要触发 workflow logic)
        """
        t = await self.repo.get_by_id(timer_id)
        if not t:
            return False
        if t.status != "scheduled":
            return False
        t.status = "fired"
        await self.repo.update(t)
        return True

    async def delete_timer(self, timer_id: str) -> bool:
        """
        物理删除, 如果不想物理删, 也可以只更新 status
        """
        return await self.repo.delete(timer_id)

    async def list_timers_for_run(self, run_id: str) -> List[Timer]:
        return await self.repo.list_by_run_id(run_id)

    async def find_due_timers(self, cutoff_time: datetime) -> List[Timer]:
        """
        找到需要触发的定时器 (fire_at <= cutoff_time && status='scheduled')
        """
        return await self.repo.list_scheduled_before(cutoff_time)