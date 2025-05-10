from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from stepflow.persistence.models import WorkflowTemplate
from stepflow.persistence.repositories.base_repository import BaseRepository

class WorkflowTemplateRepository(BaseRepository[WorkflowTemplate]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, WorkflowTemplate)

    def get_id_attribute(self) -> str:
        return "template_id"

    async def list_by_name(self, name: str) -> List[WorkflowTemplate]:
        stmt = select(WorkflowTemplate).where(WorkflowTemplate.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().all()