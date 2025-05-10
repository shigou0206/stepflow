import json
from typing import Optional, List
from stepflow.persistence.models import WorkflowEvent
from stepflow.persistence.repositories.workflow_event_repository import WorkflowEventRepository

class WorkflowEventService:
    def __init__(self, repo: WorkflowEventRepository):
        self.repo = repo

    async def record_event(
        self,
        run_id: str,
        shard_id: int,
        event_id: int,
        event_type: str,
        attributes: dict,
        archived: bool = False,
    ) -> WorkflowEvent:
        """
        插入新的事件记录，自动处理 timestamp 和 version 字段
        - event_id: 业务事件序号（非主键）
        - attributes: dict，会自动序列化为 JSON 字符串
        """
        evt = WorkflowEvent(
            run_id=run_id,
            shard_id=shard_id,
            event_id=event_id,
            event_type=event_type,
            attributes=json.dumps(attributes, ensure_ascii=False),
            archived=archived,
        )
        return await self.repo.create(evt)

    async def get_event(self, db_id: int) -> Optional[WorkflowEvent]:
        """通过数据库自增 ID 获取事件"""
        return await self.repo.get_by_id(db_id)

    async def list_events_for_run(self, run_id: str) -> List[WorkflowEvent]:
        """按 run_id 查询所有事件"""
        return await self.repo.list_by_run_id(run_id)

    async def archive_event(self, db_id: int) -> bool:
        """将某事件标记为已归档"""
        evt = await self.repo.get_by_id(db_id)
        if not evt:
            return False
        evt.archived = True
        await self.repo.update_full(evt)
        return True

    async def delete_event(self, db_id: int) -> bool:
        """删除事件"""
        return await self.repo.delete(db_id)