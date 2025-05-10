
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class EventType(str, Enum):
    # System workflow lifecycle events
    WorkflowStart = "WorkflowStart"
    WorkflowEnd = "WorkflowEnd"
    NodeEnter = "NodeEnter"
    NodeSuccess = "NodeSuccess"
    NodeFail = "NodeFail"
    Transition = "Transition"
    WorkflowControl = "WorkflowControl"

    # Optional: user-defined or system-meta events
    SignalReceived = "SignalReceived"
    Log = "Log"
    Metric = "Metric"


class EventEnvelope(BaseModel):
    run_id: str
    shard_id: int
    event_id: int  # Sequence ID within the workflow run
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    state_id: Optional[str] = None       # for node-related events
    state_type: Optional[str] = None     # e.g. Task, Pass, Choice
    trace_id: Optional[str] = None       # optional for linking parallel branches or flows
    parent_event_id: Optional[int] = None  # chain structure

    context_version: Optional[int] = None   # version of input/context
    attributes: Dict[str, Any] = Field(default_factory=dict)


class EventBus:
    async def publish(self, event: EventEnvelope) -> None:
        raise NotImplementedError

    async def publish_batch(self, events: list[EventEnvelope]) -> None:
        raise NotImplementedError
