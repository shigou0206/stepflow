from datetime import datetime, UTC
from stepflow.events.eventbus_model import EventEnvelope, EventType
from stepflow.hooks.base import ExecutionHooks
from stepflow.events.workflow_control import WorkflowControlType


class EventHookExecutor(ExecutionHooks):
    def __init__(self, event_bus, shard_id: int):
        self.bus = event_bus
        self.shard_id = shard_id
        self._event_id = 0

    async def _emit(self, run_id, event_type, **attrs):
        self._event_id += 1
        await self.bus.publish(EventEnvelope(
            run_id=run_id,
            shard_id=self.shard_id,
            event_id=self._event_id,
            event_type=event_type,
            timestamp=datetime.now(UTC),
            attributes=attrs,
            state_id=attrs.get("state_id"),
            state_type=attrs.get("state_type"),
            trace_id=attrs.get("trace_id"),
            parent_event_id=attrs.get("parent_event_id")
        ))

    async def on_workflow_start(self, run_id):
        await self._emit(run_id, EventType.WorkflowStart)

    async def on_node_enter(self, run_id, state_id, input):
        await self._emit(run_id, EventType.NodeEnter, state_id=state_id, input=input)

    async def on_node_success(self, run_id, state_id, output):
        await self._emit(run_id, EventType.NodeSuccess, state_id=state_id, output=output)

    async def on_node_fail(self, run_id, state_id, error):
        await self._emit(run_id, EventType.NodeFail, state_id=state_id, error=error)

    async def on_node_dispatch(self, run_id, state_id, input):
        await self._emit(run_id, EventType.NodeDispatch, state_id=state_id, input=input)

    async def on_workflow_end(self, run_id, status):
        await self._emit(run_id, EventType.WorkflowEnd, status=status)

    async def on_control_signal(self, run_id, signal: WorkflowControlType, reason=None):
        await self._emit(run_id, EventType.WorkflowControl, signal=signal, reason=reason)