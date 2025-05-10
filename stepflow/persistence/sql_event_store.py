
from typing import List
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from stepflow.persistence.models import WorkflowEvent
from stepflow.events.eventbus_model import EventEnvelope
from stepflow.persistence.event_store_base import EventStore


class SqlAlchemyEventStore(EventStore):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_event(self, event: EventEnvelope):
        attr = dict(event.attributes)
        for field in ["state_id", "state_type", "trace_id", "parent_event_id", "context_version"]:
            value = getattr(event, field, None)
            if value is not None:
                attr[field] = value

        model = WorkflowEvent(
            run_id=event.run_id,
            shard_id=event.shard_id,
            event_id=event.event_id,
            event_type=event.event_type.value,
            attributes=json.dumps(attr, ensure_ascii=False),
            timestamp=event.timestamp,
            archived=False,
        )
        self.db.add(model)
        await self.db.commit()

    async def save_events(self, events: List[EventEnvelope]):
        models = []
        for e in events:
            attr = dict(e.attributes)
            for field in ["state_id", "state_type", "trace_id", "parent_event_id", "context_version"]:
                value = getattr(e, field, None)
                if value is not None:
                    attr[field] = value

            models.append(WorkflowEvent(
                run_id=e.run_id,
                shard_id=e.shard_id,
                event_id=e.event_id,
                event_type=e.event_type.value,
                attributes=json.dumps(attr, ensure_ascii=False),
                timestamp=e.timestamp,
                archived=False,
            ))

        self.db.add_all(models)
        await self.db.commit()

    async def load_events(self, run_id: str) -> List[EventEnvelope]:
        result = await self.db.execute(
            select(WorkflowEvent).where(WorkflowEvent.run_id == run_id).order_by(WorkflowEvent.event_id)
        )
        rows = result.scalars().all()

        envelopes = []
        for row in rows:
            attr = json.loads(row.attributes)
            envelopes.append(EventEnvelope(
                run_id=row.run_id,
                shard_id=row.shard_id,
                event_id=row.event_id,
                event_type=row.event_type,
                timestamp=row.timestamp,
                state_id=attr.get("state_id"),
                state_type=attr.get("state_type"),
                trace_id=attr.get("trace_id"),
                parent_event_id=attr.get("parent_event_id"),
                context_version=attr.get("context_version"),
                attributes=attr
            ))

        return envelopes

    async def get_last_event_id(self, run_id: str) -> int:
        result = await self.db.execute(
            select(func.max(WorkflowEvent.event_id)).where(WorkflowEvent.run_id == run_id)
        )
        return result.scalar() or 0
