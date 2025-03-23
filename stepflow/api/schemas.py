# stepflow/api/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union

class RetryDef(BaseModel):
    ErrorEquals: List[str]
    IntervalSeconds: Optional[int] = 1
    MaxAttempts: Optional[int] = 3
    BackoffRate: Optional[float] = 2.0

class CatchDef(BaseModel):
    ErrorEquals: List[str]
    Next: str

class StateBase(BaseModel):
    Type: str
    Resource: Optional[str] = None
    InputPath: Optional[str] = None
    ResultPath: Optional[str] = None
    OutputPath: Optional[str] = None
    Parameters: Optional[Dict[str, Any]] = {}
    Retry: Optional[List[RetryDef]] = None
    Catch: Optional[List[CatchDef]] = None

class PassState(StateBase):
    Type: str = "Pass"
    Result: Optional[Dict[str, Any]] = None
    Next: str

class TaskState(StateBase):
    Type: str = "Task"
    Resource: str
    Parameters: Dict[str, Any]
    Next: str

class SucceedState(StateBase):
    Type: str = "Succeed"
    Next: Optional[str] = None

class WorkflowDef(BaseModel):
    StartAt: str
    States: Dict[str, Union[PassState, TaskState, SucceedState]]