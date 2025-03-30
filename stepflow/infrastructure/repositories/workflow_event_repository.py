# stepflow/infrastructure/repositories/workflow_event_repository.py

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from stepflow.infrastructure.models import WorkflowEvent

class WorkflowEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event: WorkflowEvent) -> WorkflowEvent:
        """
        插入新的事件记录并提交.
        """
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_by_id(self, event_id_pk: int) -> Optional[WorkflowEvent]:
        """
        根据主键 'id' 获取事件 (注意: 这里的event_id_pk指的是id字段,
        与 'event_id'(业务字段)不同).
        """
        stmt = select(WorkflowEvent).where(WorkflowEvent.id == event_id_pk)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_run_id(self, run_id: str) -> List[WorkflowEvent]:
        """
        列出同一个 run_id 的所有事件, 按 id(或 event_id)排序
        """
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.run_id == run_id)
            .order_by(WorkflowEvent.id.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_shard_and_run(self, shard_id: int, run_id: str) -> List[WorkflowEvent]:
        """
        按分片ID与 run_id 检索事件.
        """
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.shard_id == shard_id, WorkflowEvent.run_id == run_id)
            .order_by(WorkflowEvent.id.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(self, event_id_pk: int) -> bool:
        """
        根据主键id删除记录, 返回是否删除成功.
        """
        evt = await self.get_by_id(event_id_pk)
        if not evt:
            return False
        await self.db.delete(evt)
        await self.db.commit()
        return True

    async def update(self, event: WorkflowEvent) -> WorkflowEvent:
        """
        对已在session中的 event 做修改后, commit & refresh.
        """
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def list_archived(self) -> List[WorkflowEvent]:
        """
        列出 archived=True (或=1) 的事件.
        """
        stmt = (
            select(WorkflowEvent)
            .where(WorkflowEvent.archived == True)
            .order_by(WorkflowEvent.id.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()