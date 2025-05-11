from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.persistence.models import WorkflowExecution
from stepflow.persistence.repositories.base_repository import BaseRepository


class WorkflowExecutionRepository(BaseRepository[WorkflowExecution]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, WorkflowExecution)

    def get_id_attribute(self) -> str:
        return "run_id"

    async def get_by_run_id(self, run_id: str) -> Optional[WorkflowExecution]:
        return await self.get_by_id(run_id)

    async def list_by_status(self, status: str) -> List[WorkflowExecution]:
        stmt = select(WorkflowExecution).where(WorkflowExecution.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all(self) -> List[WorkflowExecution]:
        return await super().list_all()
    
    async def update_state_and_version(
        self,
        run_id: str,
        new_state: str,
        expected_version: int
    ) -> bool:
        stmt = (
            update(WorkflowExecution)
            .where(
                WorkflowExecution.run_id == run_id,
                WorkflowExecution.version == expected_version
            )
            .values(
                current_state_name=new_state,
                version=expected_version + 1
            )
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount == 1
    