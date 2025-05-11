import json
from typing import Optional, List, Union, Dict
from stepflow.persistence.models import WorkflowEvent
from stepflow.persistence.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.events.eventbus_model import EventType


class WorkflowEventService:
    def __init__(self, repo: WorkflowEventRepository):
        self.repo = repo
        self._event_id_map: Dict[str, int] = {}

    async def next_event_id(self, run_id: str) -> int:
        exec_ = await self.repo.get_by_run_id(run_id)
        if not exec_:
            raise ValueError(f"No execution found: {run_id}")
        exec_.current_event_id += 1
        await self.repo.update(exec_)
        return exec_.current_event_id

    async def record_event(
        self,
        run_id: str,
        shard_id: int,
        event_id: int,
        event_type: Union[EventType, str],
        attributes: Union[str, dict],
        archived: bool = False,
    ) -> WorkflowEvent:
        """
        标准写入事件，支持 dict 或 str 类型的 attributes。
        """
        attr_str = (
            attributes if isinstance(attributes, str)
            else json.dumps(attributes, ensure_ascii=False)
        )

        evt = WorkflowEvent(
            run_id=run_id,
            shard_id=shard_id,
            event_id=event_id,
            event_type=event_type.value if isinstance(event_type, EventType) else event_type,
            attributes=attr_str,
            archived=archived,
        )
        return await self.repo.create(evt)

    async def record_raw_event(
        self,
        event: WorkflowEvent
    ) -> WorkflowEvent:
        """允许直接写入已构造的 Event 对象"""
        return await self.repo.create(event)

    async def get_event(self, db_id: int) -> Optional[WorkflowEvent]:
        return await self.repo.get_by_id(db_id)

    async def list_events_for_run(self, run_id: str) -> List[WorkflowEvent]:
        return await self.repo.list_by_run_id(run_id)

    async def archive_event(self, db_id: int) -> bool:
        evt = await self.repo.get_by_id(db_id)
        if not evt:
            return False
        evt.archived = True
        await self.repo.update_full(evt)
        return True

    async def delete_event(self, db_id: int) -> bool:
        return await self.repo.delete(db_id)