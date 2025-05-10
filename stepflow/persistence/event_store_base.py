
from abc import ABC, abstractmethod
from typing import List
from stepflow.events.eventbus_model import EventEnvelope


class EventStore(ABC):
    @abstractmethod
    async def save_event(self, event: EventEnvelope): ...

    @abstractmethod
    async def save_events(self, events: List[EventEnvelope]): ...

    @abstractmethod
    async def load_events(self, run_id: str) -> List[EventEnvelope]: ...

    @abstractmethod
    async def get_last_event_id(self, run_id: str) -> int: ...
