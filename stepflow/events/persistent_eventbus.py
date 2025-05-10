
from typing import List
from stepflow.events.eventbus_model import EventEnvelope, EventType
from stepflow.events.base import EventBus
from stepflow.persistence.event_store_base import EventStore


class PersistentEventBus(EventBus):
    def __init__(self, store: EventStore):
        self.store = store
        self._log: List[EventEnvelope] = []

    async def publish(self, event: EventEnvelope):
        await self.store.save_event(event)
        self._log.append(event)

    async def publish_batch(self, events: List[EventEnvelope]):
        await self.store.save_events(events)
        self._log.extend(events)

    def subscribe(self, *args, **kwargs):
        raise NotImplementedError("PersistentEventBus does not support subscriptions")

    async def start(self):
        pass  # no dispatcher needed

    async def shutdown(self):
        pass  # no action needed

    def get_event_log(self) -> List[EventEnvelope]:
        return self._log
