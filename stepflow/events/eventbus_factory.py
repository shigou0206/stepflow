
from stepflow.events.base import EventBus
from stepflow.events.in_memory_eventbus import InMemoryEventBus
from stepflow.events.persistent_eventbus import PersistentEventBus
from sqlalchemy.ext.asyncio import AsyncSession


class EventBusFactory:
    @staticmethod
    def create(bus_type: str = "memory", db_session: AsyncSession = None) -> EventBus:
        if bus_type == "memory":
            return InMemoryEventBus()
        elif bus_type == "persistent":
            if db_session is None:
                raise ValueError("db_session is required for persistent event bus")
            return PersistentEventBus(db_session=db_session)
        else:
            raise ValueError(f"Unsupported event bus type: {bus_type}")
