
from typing import Callable, List, Dict
from collections import defaultdict
from asyncio import Queue, Task, create_task
import inspect

from stepflow.events.eventbus_model import EventEnvelope, EventType
from stepflow.events.base import EventBus


class InMemoryEventBus(EventBus):
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable[[EventEnvelope], None]]] = defaultdict(list)
        self.event_log: List[EventEnvelope] = []
        self.event_queue: Queue[EventEnvelope] = Queue()
        self.dispatcher: Task | None = None

    def subscribe(self, event_type: EventType, handler: Callable[[EventEnvelope], None]):
        self.subscribers[event_type].append(handler)

    async def publish(self, event: EventEnvelope):
        self.event_log.append(event)
        await self.event_queue.put(event)

    async def publish_batch(self, events: List[EventEnvelope]):
        for e in events:
            await self.publish(e)

    async def start(self):
        self.dispatcher = create_task(self._dispatch_loop())

    async def shutdown(self):
        if self.dispatcher:
            self.dispatcher.cancel()
            await self.event_queue.join()

    async def _dispatch_loop(self):
        while True:
            event = await self.event_queue.get()
            for handler in self.subscribers.get(event.event_type, []):
                try:
                    if inspect.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    print(f"[EventBus] Handler error: {e}")
            self.event_queue.task_done()

    def get_event_log(self) -> List[EventEnvelope]:
        return self.event_log
