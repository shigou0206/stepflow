
from stepflow.dsl.dsl_model import WorkflowDSL, TaskState, CustomState, PassState, SucceedState, FailState
from typing import Optional, Dict, Any
from pydantic import BaseModel


class Command(BaseModel):
    type: str  # e.g., ExecuteTask, Succeed, Fail, Wait, Goto
    state_name: str
    next_state: Optional[str] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    resource: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    raw_state: Optional[dict] = None


def step_once(dsl: WorkflowDSL, state_name: str, context: dict) -> Command:
    state = dsl.states[state_name]

    if isinstance(state, TaskState) or isinstance(state, CustomState):
        return Command(
            type="ExecuteTask",
            state_name=state_name,
            next_state=state.next,
            resource=state.resource
        )

    if isinstance(state, PassState):
        result = state.result or {}
        if state.end is True and not state.next:
            return Command(type="Succeed", output=result, state_name=state_name)
        else:
            return Command(type="Pass", output=result, state_name=state_name, next_state=state.next)

    if isinstance(state, SucceedState):
        return Command(type="Succeed", output=context, state_name=state_name)

    if isinstance(state, FailState):
        return Command(type="Fail", state_name=state_name, error=state.error, output=context, cause=state.cause)

    # You can add logic here for ChoiceState, MapState, ParallelState if needed
    raise NotImplementedError(f"Unsupported state type: {type(state).__name__}")
