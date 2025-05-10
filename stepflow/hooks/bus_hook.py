from datetime import datetime, timezone
from stepflow.hooks.base import ExecutionHooks
from stepflow.events.base import EventBus
from stepflow.events.eventbus_model import EventType, EventEnvelope


class BusHook(ExecutionHooks):
    def __init__(self, bus: EventBus, shard_id: int = 0):
        self.bus = bus
        self.shard_id = shard_id
        self._event_id_counter = {}

    def _next_event_id(self, run_id: str) -> int:
        self._event_id_counter.setdefault(run_id, 0)
        self._event_id_counter[run_id] += 1
        return self._event_id_counter[run_id]

    async def on_workflow_start(self, run_id: str):
        await self._publish(run_id, EventType.WorkflowStart, {})

    async def on_node_enter(self, run_id: str, state_name: str, input):
        await self._publish(run_id, EventType.NodeEnter, {
            "state_id": state_name,
            "input": input
        })

    async def on_node_success(self, run_id: str, state_name: str, output):
        await self._publish(run_id, EventType.NodeSuccess, {
            "state_id": state_name,
            "output": output
        })

    async def on_node_fail(self, run_id: str, state_name: str, error: str):
        await self._publish(run_id, EventType.NodeFail, {
            "state_id": state_name,
            "error": error
        })

    async def on_workflow_end(self, run_id: str, result):
        await self._publish(run_id, EventType.WorkflowEnd, {
            "result": result
        })

    async def on_control_signal(self, run_id: str, signal_type: str, reason: str):
        await self._publish(run_id, EventType.WorkflowControl, {
            "signal": signal_type,
            "reason": reason
        })

    async def _publish(self, run_id: str, event_type: EventType, attributes: dict):
        evt = EventEnvelope(
            run_id=run_id,
            shard_id=self.shard_id,
            event_id=self._next_event_id(run_id),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            attributes=attributes,
            state_id=attributes.get("state_id"),
            state_type=None  # 可扩展
        )
        await self.bus.publish(evt)