from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stepflow.persistence.models import WorkflowVisibility
from stepflow.persistence.repositories.base_repository import BaseRepository

class WorkflowVisibilityRepository(BaseRepository[WorkflowVisibility]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, WorkflowVisibility)

    def get_id_attribute(self) -> str:
        return "run_id"

    async def get_by_run_id(self, run_id: str) -> Optional[WorkflowVisibility]:
        return await self.get_by_id(run_id)

    async def list_by_status(self, status: str) -> List[WorkflowVisibility]:
        stmt = select(WorkflowVisibility).where(WorkflowVisibility.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()