from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.models import WorkflowEvent
from stepflow.persistence.repositories.base_repository import BaseRepository


class WorkflowEventRepository(BaseRepository[WorkflowEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, WorkflowEvent)

    def get_id_attribute(self) -> str:
        return "id"

    async def list_by_run_id(self, run_id: str) -> List[WorkflowEvent]:
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.run_id == run_id)
            .order_by(WorkflowEvent.id.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_shard_and_run(self, shard_id: int, run_id: str) -> List[WorkflowEvent]:
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.shard_id == shard_id, WorkflowEvent.run_id == run_id)
            .order_by(WorkflowEvent.id.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_archived(self) -> List[WorkflowEvent]:
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.archived == True)
            .order_by(WorkflowEvent.id.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, event_id_pk: int) -> Optional[WorkflowEvent]:
        # 明确 override 支持类型提示
        return await super().get_by_id(event_id_pk)