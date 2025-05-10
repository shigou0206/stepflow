
from abc import ABC, abstractmethod
from typing import Callable, List
from stepflow.events.eventbus_model import EventEnvelope, EventType


class EventBus(ABC):

    @abstractmethod
    async def publish(self, event: EventEnvelope) -> None: ...

    @abstractmethod
    async def publish_batch(self, events: List[EventEnvelope]) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: EventType, handler: Callable[[EventEnvelope], None]) -> None: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...
