from typing import Dict, List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field, model_validator, field_validator, ValidationInfo, TypeAdapter, ConfigDict

# -----------------------------
# alias generator
# -----------------------------

def to_pascal_case(s: str) -> str:
    return ''.join(word.capitalize() for word in s.split('_'))

class DSLBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_pascal_case,
        populate_by_name=True
    )

# -----------------------------
# Retry & Catch Policies
# -----------------------------

class RetryPolicy(DSLBase):
    error_equals: List[Literal["TimeoutError", "TaskFailed", "HeartbeatTimeout", "AnyError"]]
    interval_seconds: Optional[int] = 1
    backoff_rate: Optional[float] = 2.0
    max_attempts: Optional[int] = 3

class CatchPolicy(DSLBase):
    error_equals: List[Literal["TimeoutError", "TaskFailed", "HeartbeatTimeout", "AnyError"]]
    next: str
    result_path: Optional[str] = None

# -----------------------------
# Base State
# -----------------------------

class BaseState(DSLBase):
    comment: Optional[str] = None
    input_expr: Optional[str] = None
    output_expr: Optional[str] = None
    result_expr: Optional[str] = None
    retry: Optional[List[RetryPolicy]] = None
    catch: Optional[List[CatchPolicy]] = None
    next: Optional[str] = None
    end: Optional[bool] = None

# -----------------------------
# Specific State Types
# -----------------------------

class TaskState(BaseState):
    type: Literal["Task"]
    resource: str
    parameters: Optional[Dict[str, Union[str, int, float, bool, list, dict, None]]] = None
    execution_config: Optional[Dict[str, Union[str, int, float, bool]]] = None
    heartbeat_seconds: Optional[int] = None
    heartbeat_expr: Optional[str] = None

    @model_validator(mode='after')
    def must_have_next_or_end(self):
        if not self.next and not self.end:
            raise ValueError("TaskState must define either next or end")
        if self.next and self.end:
            raise ValueError("TaskState cannot define both next and end")
        return self

class PassState(BaseState):
    type: Literal["Pass"]
    result: Optional[Union[str, int, float, dict, list, bool]] = None
    result_path: Optional[str] = None

    @model_validator(mode='after')
    def must_have_next_or_end(self):
        if not self.next and not self.end:
            raise ValueError("PassState must define either next or end")
        if self.next and self.end:
            raise ValueError("PassState cannot define both next and end")
        return self

class WaitState(BaseState):
    type: Literal["Wait"]
    seconds: Optional[int] = None
    timestamp: Optional[str] = None

    @model_validator(mode='after')
    def validate_wait_config(self):
        if not self.seconds and not self.timestamp:
            raise ValueError("WaitState must define either seconds or timestamp")
        if self.seconds and self.timestamp:
            raise ValueError("WaitState cannot define both seconds and timestamp")
        if not self.next and not self.end:
            raise ValueError("WaitState must define either next or end")
        if self.next and self.end:
            raise ValueError("WaitState cannot define both next and end")
        return self

class ChoiceLogic(DSLBase):
    and_: Optional[List["ChoiceLogic"]] = Field(None, alias="And")
    or_: Optional[List["ChoiceLogic"]] = Field(None, alias="Or")
    not_: Optional["ChoiceLogic"] = Field(None, alias="Not")
    variable: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[Union[str, int, float, bool]] = None

class ChoiceRule(DSLBase):
    condition: ChoiceLogic
    next: str

class ChoiceState(BaseState):
    type: Literal["Choice"]
    choices: List[ChoiceRule]
    default: Optional[str] = None

class SucceedState(BaseState):
    type: Literal["Succeed"]

class FailState(BaseState):
    type: Literal["Fail"]
    error: Optional[str] = None
    cause: Optional[str] = None

class Branch(DSLBase):
    start_at: str
    states: Dict[str, 'State']

class ParallelState(BaseState):
    type: Literal["Parallel"]
    branches: List[Branch]
    max_concurrency: Optional[int] = None

    @model_validator(mode='after')
    def must_have_next_or_end(self):
        if not self.next and not self.end:
            raise ValueError("ParallelState must define either next or end")
        if self.next and self.end:
            raise ValueError("ParallelState cannot define both next and end")
        return self

class MapState(BaseState):
    type: Literal["Map"]
    items_path: str
    iterator: Branch
    max_concurrency: Optional[int] = None

    @model_validator(mode='after')
    def must_have_next_or_end(self):
        if not self.next and not self.end:
            raise ValueError("MapState must define either next or end")
        if self.next and self.end:
            raise ValueError("MapState cannot define both next and end")
        return self

class CustomState(BaseState):
    type: Literal["Custom"]
    resource: str
    custom_config: Optional[dict] = None

    @model_validator(mode='after')
    def check_custom_state(self):
        if self.resource and not self.resource.startswith("plugin:"):
            raise ValueError("CustomState.resource must start with 'plugin:'")
        if not self.next and not self.end:
            raise ValueError("CustomState must define either next or end")
        if self.next and self.end:
            raise ValueError("CustomState cannot define both next and end")
        return self

# -----------------------------
# Union for State
# -----------------------------

State = Annotated[
    Union[
        TaskState,
        PassState,
        WaitState,
        ChoiceState,
        SucceedState,
        FailState,
        ParallelState,
        MapState,
        CustomState,
    ],
    Field(discriminator="type")
]

# -----------------------------
# Workflow DSL Root
# -----------------------------

class WorkflowDSL(DSLBase):
    comment: Optional[str] = None
    version: Optional[str] = "1.0.0"
    start_at: str
    global_config: Optional[dict] = None
    error_handling: Optional[dict] = None
    states: Dict[str, State]

    @field_validator("states", mode="before")
    @classmethod
    def parse_states(cls, raw: dict, info: ValidationInfo):
        adapter = TypeAdapter(State)
        return {k: adapter.validate_python(v) for k, v in raw.items()}

# allow recursive references
ChoiceLogic.model_rebuild()
