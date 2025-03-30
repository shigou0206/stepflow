# stepflow/domain/dsl_model.py
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from typing_extensions import Literal

#
# 1. Retry & Catch
#
class RetryPolicy(BaseModel):
    ErrorEquals: List[str]
    IntervalSeconds: int = 1
    BackoffRate: float = 2.0
    MaxAttempts: int = 3

class CatchDefinition(BaseModel):
    ErrorEquals: List[str]
    Next: str

#
# 2. 各种状态类型
#
class TaskState(BaseModel):
    Type: Literal["Task"]
    ActivityType: str
    InputPath: Optional[str] = "$"
    ResultPath: Optional[str] = "$"
    OutputPath: Optional[str] = "$"
    Retry: Optional[List[RetryPolicy]] = None
    Catch: Optional[List[CatchDefinition]] = None
    Next: Optional[str] = None
    End: bool = False

class ChoiceRule(BaseModel):
    Variable: str
    StringEquals: Optional[str] = None
    # 其它条件 NumericEquals, etc.
    Next: str

class ChoiceState(BaseModel):
    Type: Literal["Choice"]
    InputPath: Optional[str] = "$"
    Choices: List[ChoiceRule]
    Default: Optional[str] = None

class WaitState(BaseModel):
    Type: Literal["Wait"]
    InputPath: Optional[str] = "$"
    Seconds: Optional[int] = None
    Next: Optional[str] = None
    End: bool = False

class PassState(BaseModel):
    Type: Literal["Pass"]
    InputPath: Optional[str] = "$"
    Result: Optional[dict] = None
    ResultPath: Optional[str] = "$"
    OutputPath: Optional[str] = "$"
    Next: Optional[str] = None
    End: bool = False

class ParallelBranch(BaseModel):
    StartAt: str
    States: Dict[str, Union["TaskState", "ChoiceState", "WaitState", "ParallelState", "PassState", "FailState", "SucceedState"]]

class ParallelState(BaseModel):
    Type: Literal["Parallel"]
    InputPath: Optional[str] = "$"
    Branches: List[ParallelBranch]
    ResultPath: Optional[str] = "$"
    Next: Optional[str] = None
    End: bool = False

class FailState(BaseModel):
    Type: Literal["Fail"]
    Error: Optional[str] = None
    Cause: Optional[str] = None

class SucceedState(BaseModel):
    Type: Literal["Succeed"]

# 处理嵌套引用 (Parallel Branch)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    TaskState.model_rebuild()
    ChoiceState.model_rebuild()
    WaitState.model_rebuild()
    ParallelState.model_rebuild()
    PassState.model_rebuild()
    FailState.model_rebuild()
    SucceedState.model_rebuild()

# 大 Union
StateUnion = Union[TaskState, ChoiceState, WaitState, ParallelState, PassState, FailState, SucceedState]

#
# 3. 顶层 WorkflowDSL
#
class WorkflowDSL(BaseModel):
    Version: str
    Name: str
    StartAt: str
    Description: Optional[str] = None
    TimeoutSeconds: Optional[int] = None
    GlobalRetryPolicy: Optional[RetryPolicy] = None
    OutputPath: Optional[str] = "$"
    States: Dict[str, StateUnion]