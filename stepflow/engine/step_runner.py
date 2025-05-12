from stepflow.dsl.dsl_model import (
    WorkflowDSL,
    TaskState,
    CustomState,
    PassState,
    SucceedState,
    FailState,
    ChoiceState,
    ChoiceLogic
)
from typing import Optional, Dict, Any
from pydantic import BaseModel
from stepflow.expression.parameter_mapper import extract_json_path


class Command(BaseModel):
    type: str  # e.g., ExecuteTask, Succeed, Fail, Choice
    state_name: str
    next_state: Optional[str] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    cause: Optional[str] = None  # ✅ 添加字段以防 AttributeError
    resource: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    raw_state: Optional[dict] = None


COMPARISON_OPERATORS = {
    "Equals": lambda v, x: v == x,
    "NotEquals": lambda v, x: v != x,
    "GreaterThan": lambda v, x: v > x,
    "GreaterThanEquals": lambda v, x: v >= x,
    "LessThan": lambda v, x: v < x,
    "LessThanEquals": lambda v, x: v <= x,
    "StringEquals": lambda v, x: str(v) == str(x),
    "StringNotEquals": lambda v, x: str(v) != str(x),
    "IsIn": lambda v, x: v in x,
    "IsNotIn": lambda v, x: v not in x,
    "IsNull": lambda v, _: v is None,
    "IsBoolean": lambda v, _: isinstance(v, bool),
    "IsString": lambda v, _: isinstance(v, str),
    "IsNumeric": lambda v, _: isinstance(v, (int, float))
}


def evaluate_logic(logic: ChoiceLogic, context: dict) -> bool:
    if logic.and_:
        return all(evaluate_logic(cond, context) for cond in logic.and_)
    if logic.or_:
        return any(evaluate_logic(cond, context) for cond in logic.or_)
    if logic.not_:
        return not evaluate_logic(logic.not_, context)

    variable = logic.variable
    operator = logic.operator
    value = logic.value
    if variable is None or operator is None:
        return False

    target_value = extract_json_path(context, variable)
    compare_fn = COMPARISON_OPERATORS.get(operator)
    if compare_fn is None:
        raise ValueError(f"Unsupported operator: {operator}")
    return compare_fn(target_value, value)


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
        return Command(
            type="Fail",
            state_name=state_name,
            error=state.error,
            output=context,
            cause=state.cause
        )

    if isinstance(state, ChoiceState):
        for rule in state.choices:
            if evaluate_logic(rule.condition, context):
                return Command(type="Choice", state_name=state_name, next_state=rule.next)
        if state.default:
            return Command(type="Choice", state_name=state_name, next_state=state.default)
        else:
            raise ValueError(f"No matching choice and no default for state: {state_name}")

    raise NotImplementedError(f"Unsupported state type: {type(state).__name__}")