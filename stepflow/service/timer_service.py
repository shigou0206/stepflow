import uuid
from datetime import datetime
from typing import List, Optional
from stepflow.persistence.models import Timer
from stepflow.persistence.repositories.timer_repository import TimerRepository

class TimerService:
    def __init__(self, repo: TimerRepository):
        self.repo = repo

    async def schedule_timer(self, run_id: str, state_name: str, shard_id: int, fire_at: datetime) -> Timer:
        """
        创建一个新的定时器, 初始状态 scheduled。
        如果 (run_id, state_name) 已存在 scheduled/fired 状态，则跳过创建。
        """
        existing = await self.repo.get_by_run_id_and_state(run_id, state_name)
        if existing:
            return existing

        timer_id = str(uuid.uuid4())
        timer = Timer(
            timer_id=timer_id,
            run_id=run_id,
            state_name=state_name,
            shard_id=shard_id,
            fire_at=fire_at,
            status="scheduled",
        )
        return await self.repo.create(timer)

    async def get_by_run_id_and_state(self, run_id: str, state_name: str) -> Optional[Timer]:
        return await self.repo.get_by_run_id_and_state(run_id, state_name)

    async def cancel_timer(self, timer_id: str) -> bool:
        """
        将定时器状态改为 canceled（如果还未触发）
        """
        timer = await self.repo.get_by_id(timer_id)
        if not timer or timer.status != "scheduled":
            return False
        timer.status = "canceled"
        await self.repo.update(timer)
        return True

    async def fire_timer(self, timer_id: str) -> bool:
        """
        将定时器标记为 fired（若还处于 scheduled 状态）
        """
        timer = await self.repo.get_by_id(timer_id)
        if not timer or timer.status != "scheduled":
            return False
        timer.status = "fired"
        await self.repo.update(timer)
        return True

    async def delete_timer(self, timer_id: str) -> bool:
        """
        物理删除定时器
        """
        return await self.repo.delete(timer_id)

    async def list_timers_for_run(self, run_id: str) -> List[Timer]:
        """
        获取某个 workflow 实例的所有定时器
        """
        return await self.repo.list_by_run_id(run_id)

    async def find_due_timers(self, cutoff_time: datetime) -> List[Timer]:
        """
        查找 fire_at <= cutoff_time 且 status 为 scheduled 的定时器
        """
        return await self.repo.list_scheduled_before(cutoff_time)