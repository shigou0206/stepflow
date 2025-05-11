from typing import Callable, List, Dict, Union
from collections import defaultdict
from asyncio import Queue, Task, create_task, CancelledError
import inspect
import logging

from stepflow.events.eventbus_model import EventEnvelope, EventType
from stepflow.events.base import EventBus

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InMemoryEventBus(EventBus):
    def __init__(self):
        self.subscribers: Dict[Union[EventType, str], List[Callable[[EventEnvelope], None]]] = defaultdict(list)
        self.event_log: List[EventEnvelope] = []
        self.event_queue: Queue[EventEnvelope] = Queue()
        self.dispatcher: Task | None = None

    def subscribe(self, event_type: Union[EventType, str], handler: Callable[[EventEnvelope], None]):
        """订阅某类事件；event_type 可为具体类型，也可为 "*"（全部）"""
        self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: Union[EventType, str], handler: Callable[[EventEnvelope], None]):
        """取消订阅"""
        if handler in self.subscribers.get(event_type, []):
            self.subscribers[event_type].remove(handler)

    def clear(self):
        """清除所有订阅者和事件日志（常用于测试）"""
        self.subscribers.clear()
        self.event_log.clear()
        while not self.event_queue.empty():
            self.event_queue.get_nowait()

    async def publish(self, event: EventEnvelope):
        self.event_log.append(event)
        await self.event_queue.put(event)

    async def publish_batch(self, events: List[EventEnvelope]):
        for e in events:
            await self.publish(e)

    async def start(self):
        if self.dispatcher and not self.dispatcher.done():
            logger.warning("[EventBus] Dispatcher already running, start() ignored.")
            return
        logger.info("[EventBus] Dispatcher started.")
        self.dispatcher = create_task(self._dispatch_loop())

    async def shutdown(self):
        if self.dispatcher:
            logger.info("[EventBus] Waiting for queue to drain before shutdown...")
            await self.event_queue.join()
            logger.info("[EventBus] Cancelling dispatcher task...")
            self.dispatcher.cancel()
            try:
                await self.dispatcher
            except CancelledError:
                logger.info("[EventBus] Dispatcher cancelled successfully.")
            self.dispatcher = None

    async def _dispatch_loop(self):
        try:
            while True:
                event = await self.event_queue.get()
                handlers = (
                    self.subscribers.get(event.event_type, []) +
                    self.subscribers.get("*", [])
                )
                for handler in handlers:
                    try:
                        if inspect.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        logger.exception(f"[EventBus] Error in handler for {event.event_type}: {e}")
                self.event_queue.task_done()
        except CancelledError:
            logger.info("[EventBus] Dispatch loop cancelled.")

    def get_event_log(self) -> List[EventEnvelope]:
        return self.event_log