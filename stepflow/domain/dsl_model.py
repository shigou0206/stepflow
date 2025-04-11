# stepflow/domain/dsl_model.py
from typing import Dict, List, Optional, Union, Any
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
class StateBase(BaseModel):
    """状态基类"""
    Type: str
    Comment: Optional[str] = None
    InputPath: Optional[str] = None
    OutputPath: Optional[str] = None
    ResultPath: Optional[str] = None
    Next: Optional[str] = None
    End: Optional[bool] = None

class TaskState(StateBase):
    """任务状态"""
    Type: str = "Task"
    Resource: Optional[str] = None
    ActivityType: Optional[str] = None  # 自定义字段，指定活动类型
    Parameters: Optional[Dict[str, Any]] = None  # 添加 Parameters 属性
    Retry: Optional[List[Dict[str, Any]]] = None
    Catch: Optional[List[Dict[str, Any]]] = None
    TimeoutSeconds: Optional[int] = None
    HeartbeatSeconds: Optional[int] = None

class ChoiceRule(BaseModel):
    Variable: str
    StringEquals: Optional[str] = None
    # 其它条件 NumericEquals, etc.
    Next: str

class ChoiceState(StateBase):
    """选择状态"""
    Type: str = "Choice"
    Choices: List[Dict[str, Any]]
    Default: Optional[str] = None

class WaitState(StateBase):
    """等待状态"""
    Type: str = "Wait"
    Seconds: Optional[int] = None
    SecondsPath: Optional[str] = None
    Timestamp: Optional[str] = None
    TimestampPath: Optional[str] = None

class PassState(StateBase):
    """传递状态"""
    Type: str = "Pass"
    Result: Optional[Any] = None
    ResultPath: Optional[str] = None

class ParallelBranch(BaseModel):
    StartAt: str
    States: Dict[str, Union["TaskState", "ChoiceState", "WaitState", "ParallelState", "PassState", "FailState", "SucceedState"]]

class ParallelState(StateBase):
    """并行状态"""
    Type: str = "Parallel"
    Branches: List[Dict[str, Any]]
    Retry: Optional[List[Dict[str, Any]]] = None
    Catch: Optional[List[Dict[str, Any]]] = None

class FailState(StateBase):
    """失败状态"""
    Type: str = "Fail"
    Error: Optional[str] = None
    Cause: Optional[str] = None

class SucceedState(StateBase):
    """成功状态"""
    Type: str = "Succeed"

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
StateUnion = Union[
    TaskState, 
    ChoiceState, 
    WaitState, 
    ParallelState, 
    PassState, 
    FailState, 
    SucceedState
]

#
# 3. 顶层 WorkflowDSL
#
class WorkflowDSL(BaseModel):
    Version: str
    Name: Optional[str] = None
    Comment: Optional[str] = None
    StartAt: str
    States: Dict[str, StateUnion]
    TimeoutSeconds: Optional[int] = None