"""
step_runner.py  ——  把当前状态解析成下一步 Command
完全支持：
    Task / Custom
    Wait
    Pass
    Choice  (带嵌套 And / Or / Not)
    Fail
    Succeed
"""

from __future__ import annotations

from datetime import datetime, UTC, timedelta
from typing import Any, Dict, Literal, Optional, Union, List

from pydantic import BaseModel
from stepflow.dsl.dsl_model import (
    WorkflowDSL,
    TaskState,
    CustomState,
    WaitState,
    PassState,
    SucceedState,
    FailState,
    ChoiceState,
    ChoiceLogic,
)
from stepflow.expression.parameter_mapper import extract_json_path

# ------------------------------------------------------------------ #
#                       Command 数据模型
# ------------------------------------------------------------------ #

class Command(BaseModel):
    type: Literal["ExecuteTask", "Wait", "Pass", "Choice", "Succeed", "Fail"]
    state_name: str
    next_state: Optional[str] = None   # ExecuteTask / Pass / Choice / Wait
    output: Optional[Any] = None       # Pass / Succeed
    error: Optional[str] = None        # Fail
    cause: Optional[str] = None        # Fail
    resource: Optional[str] = None     # ExecuteTask
    wait_until: Optional[datetime] = None  # Wait (inline)
    seconds: Optional[int] = None          # Wait (inline)

# ------------------------------------------------------------------ #
#            Choice 比较符映射（与 AWS StepFunctions 命名一致）
# ------------------------------------------------------------------ #
def _safe_gt(a, b):      # a >  b
    return a is not None and b is not None and a >  b

def _safe_ge(a, b):      # a >= b
    return a is not None and b is not None and a >= b

def _safe_lt(a, b):      # a <  b
    return a is not None and b is not None and a <  b

def _safe_le(a, b):      # a <= b
    return a is not None and b is not None and a <= b

COMPARISON_OPERATORS: dict[str, callable] = {
    "Equals":            lambda v, x: v == x,
    "NotEquals":         lambda v, x: v != x,
    "GreaterThan":       _safe_gt,
    "GreaterThanEquals": _safe_ge,
    "LessThan":          _safe_lt,
    "LessThanEquals":    _safe_le,
    "StringEquals":      lambda v, x: str(v) == str(x),
    "StringNotEquals":   lambda v, x: str(v) != str(x),
    "IsIn":              lambda v, x: v in x,
    "IsNotIn":           lambda v, x: v not in x,
    "IsNull":            lambda v, _: v is None,
    "IsBoolean":         lambda v, _: isinstance(v, bool),
    "IsString":          lambda v, _: isinstance(v, str),
    "IsNumeric":         lambda v, _: isinstance(v, (int, float)),
}

# ------------------------------------------------------------------ #
#                 Choice 逻辑递归求值
# ------------------------------------------------------------------ #

def _eval_logic(logic: ChoiceLogic, data: dict) -> bool:
    if logic.and_:
        return all(_eval_logic(c, data) for c in logic.and_)
    if logic.or_:
        return any(_eval_logic(c, data) for c in logic.or_)
    if logic.not_:
        return not _eval_logic(logic.not_, data)

    # 叶子比较
    variable = logic.variable
    op_name = logic.operator
    value = logic.value
    if variable is None or op_name is None:
        return False

    current = extract_json_path(data, variable)
    fn = COMPARISON_OPERATORS.get(op_name)
    if fn is None:
        raise ValueError(f"Unsupported operator: {op_name}")
    return fn(current, value)

# ------------------------------------------------------------------ #
#                        核心 step_once
# ------------------------------------------------------------------ #

def step_once(dsl: WorkflowDSL, state_name: str, context: dict) -> Command:
    """
    根据当前 state_name & context 解析出下一步 Command。
    """
    state = dsl.states[state_name]

    # ----------------- Task / Custom ----------------- #
    if isinstance(state, (TaskState, CustomState)):
        return Command(
            type="ExecuteTask",
            state_name=state_name,
            next_state=state.next,
            resource=state.resource,
        )

    # ----------------- Wait -------------------------- #
    if isinstance(state, WaitState):
        # 计算 wait_until（给 inline 引用；deferred 模式 Engine 不使用它）
        if state.seconds is not None:
            wait_until = datetime.now(UTC) + timedelta(seconds=state.seconds)
            seconds = state.seconds
        elif state.timestamp is not None:
            wait_until = datetime.fromisoformat(state.timestamp)
            seconds = int((wait_until - datetime.now(UTC)).total_seconds())
            seconds = max(0, seconds)
        else:
            raise ValueError("WaitState must define Seconds or Timestamp")

        return Command(
            type="Wait",
            state_name=state_name,
            next_state=state.next,
            wait_until=wait_until,
            seconds=seconds,
        )

    # ----------------- Pass -------------------------- #
    if isinstance(state, PassState):
        result = state.result or {}
        if state.end and not state.next:
            return Command(type="Succeed", state_name=state_name, output=result)
        return Command(type="Pass", state_name=state_name, output=result, next_state=state.next)

    # ----------------- Choice ------------------------ #
    if isinstance(state, ChoiceState):
        for branch in state.choices:
            if _eval_logic(branch.condition, context):
                return Command(type="Choice", state_name=state_name, next_state=branch.next)
        if state.default:
            return Command(type="Choice", state_name=state_name, next_state=state.default)
        raise ValueError(f"No matching choice and no Default for state: {state_name}")

    # ----------------- Succeed / Fail --------------- #
    if isinstance(state, SucceedState):
        return Command(type="Succeed", state_name=state_name, output=context)

    if isinstance(state, FailState):
        return Command(
            type="Fail",
            state_name=state_name,
            error=state.error,
            cause=state.cause,
        )

    # ----------------- 未实现 ------------------------ #
    raise NotImplementedError(f"Unsupported state type: {type(state).__name__}")