# stepflow/application/workflow_event_service.py

from typing import Optional, List
from datetime import datetime
from stepflow.infrastructure.models import WorkflowEvent
from stepflow.infrastructure.repositories.workflow_event_repository import WorkflowEventRepository

class WorkflowEventService:
    def __init__(self, repo: WorkflowEventRepository):
        self.repo = repo

    async def record_event(
        self,
        run_id: str,
        shard_id: int,
        event_id: int,
        event_type: str,
        attributes: str,
        archived: bool = False
    ) -> WorkflowEvent:
        """
        将新的事件写入数据库, 并自动设置 timestamp、attr_version 等.
        event_id: 业务事件序号(从1开始递增)
        """
        evt = WorkflowEvent(
            run_id=run_id,
            shard_id=shard_id,
            event_id=event_id,
            event_type=event_type,
            attributes=attributes,
            archived=archived
        )
        return await self.repo.create(evt)

    async def get_event(self, db_id: int) -> Optional[WorkflowEvent]:
        """通过主键id(DB自动增量)来获取事件."""
        return await self.repo.get_by_id(db_id)

    async def list_events_for_run(self, run_id: str) -> List[WorkflowEvent]:
        """列出同一 run_id 的所有事件."""
        return await self.repo.list_by_run_id(run_id)

    async def archive_event(self, db_id: int) -> bool:
        """
        将某条事件标记为 archived=True
        """
        evt = await self.repo.get_by_id(db_id)
        if not evt:
            return False
        evt.archived = True
        await self.repo.update(evt)
        return True

    async def delete_event(self, db_id: int) -> bool:
        """物理删除事件"""
        return await self.repo.delete(db_id)