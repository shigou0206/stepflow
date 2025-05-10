from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from stepflow.persistence.models import ActivityTask
from stepflow.persistence.repositories.base_repository import BaseRepository


class ActivityTaskRepository(BaseRepository[ActivityTask]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ActivityTask)

    def get_id_attribute(self) -> str:
        return "task_token"

    async def get_by_task_token(self, task_token: str) -> Optional[ActivityTask]:
        return await self.get_by_id(task_token)

    async def list_by_run_id(self, run_id: str) -> List[ActivityTask]:
        stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(self, status: str, limit: Optional[int] = None) -> List[ActivityTask]:
        stmt = select(ActivityTask).where(ActivityTask.status == status)
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(self, task_token: str, status: str) -> None:
        stmt = (
            update(ActivityTask)
            .where(ActivityTask.task_token == task_token)
            .values(status=status)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_full(self, task: ActivityTask) -> ActivityTask:
        """
        更新任务的多个字段（运行信息、结果、错误等）
        """
        stmt = (
            update(ActivityTask)
            .where(ActivityTask.task_token == task.task_token)
            .values(
                status=task.status,
                result=task.result,
                error=task.error,
                error_details=task.error_details,
                started_at=task.started_at,
                completed_at=task.completed_at,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(task.task_token)