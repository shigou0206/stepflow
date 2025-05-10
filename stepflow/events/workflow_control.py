
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, UTC


class WorkflowControlType(str, Enum):
    Cancel = "Cancel"
    Terminate = "Terminate"
    Pause = "Pause"
    Resume = "Resume"


@dataclass
class WorkflowControlSignal:
    control_type: WorkflowControlType
    reason: Optional[str] = None
    timestamp: datetime = datetime.now(UTC)


class ExecutionContext:
    def __init__(self):
        self._canceled = False
        self._terminated = False
        self._paused = False

    def apply_control(self, signal: WorkflowControlSignal):
        if signal.control_type == WorkflowControlType.Cancel:
            self._canceled = True
        elif signal.control_type == WorkflowControlType.Terminate:
            self._terminated = True
        elif signal.control_type == WorkflowControlType.Pause:
            self._paused = True
        elif signal.control_type == WorkflowControlType.Resume:
            self._paused = False

    def is_canceled(self) -> bool:
        return self._canceled

    def is_terminated(self) -> bool:
        return self._terminated

    def is_paused(self) -> bool:
        return self._paused

    def check_interrupt(self):
        if self._terminated:
            raise RuntimeError("Workflow terminated")
        if self._canceled:
            raise RuntimeError("Workflow canceled")
        if self._paused:
            raise RuntimeError("Workflow paused")
