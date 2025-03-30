# stepflow/infrastructure/repositories/workflow_visibility_repository.py

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from stepflow.infrastructure.models import WorkflowVisibility

class WorkflowVisibilityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, vis: WorkflowVisibility) -> WorkflowVisibility:
        """
        插入新的可见性记录
        """
        self.db.add(vis)
        await self.db.commit()
        await self.db.refresh(vis)
        return vis

    async def get_by_run_id(self, run_id: str) -> Optional[WorkflowVisibility]:
        """
        根据 run_id 获取可见性记录
        """
        stmt = select(WorkflowVisibility).where(WorkflowVisibility.run_id == run_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, vis: WorkflowVisibility) -> WorkflowVisibility:
        """
        提交对已在session中的对象的修改
        """
        await self.db.commit()
        await self.db.refresh(vis)
        return vis

    async def delete(self, run_id: str) -> bool:
        """
        物理删除可见性记录
        """
        obj = await self.get_by_run_id(run_id)
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True

    async def list_by_status(self, status: str) -> List[WorkflowVisibility]:
        """
        按状态查询, 例如 'running', 'completed', ...
        """
        stmt = select(WorkflowVisibility).where(WorkflowVisibility.status == status)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_all(self) -> List[WorkflowVisibility]:
        """
        简单列出所有记录 (小规模适用, 大规模需分页)
        """
        stmt = select(WorkflowVisibility)
        result = await self.db.execute(stmt)
        return result.scalars().all()