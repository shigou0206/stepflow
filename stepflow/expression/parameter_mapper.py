
from typing import Any, Optional
from jsonpath_ng.ext import parse


class ExpressionEvaluationError(Exception):
    pass


def evaluate_expr(data: Any, expr: Optional[str]) -> Any:
    """
    Evaluate a JSONPath expression against input data.
    Returns the first match if multiple found.
    """
    if not expr:
        return data
    try:
        jsonpath_expr = parse(expr)
        matches = [match.value for match in jsonpath_expr.find(data)]
        if not matches:
            return None
        return matches[0] if len(matches) == 1 else matches
    except Exception as e:
        raise ExpressionEvaluationError(f"Error evaluating expression '{expr}': {e}")


def apply_parameters(input_data: Any, parameters: dict, input_expr: Optional[str]) -> dict:
    """
    Apply InputExpr to extract part of input_data, and merge with static parameters.
    """
    extracted = evaluate_expr(input_data, input_expr)
    if not isinstance(extracted, dict):
        return parameters or {}
    return {**extracted, **(parameters or {})}


def apply_result_expr(result_data: Any, result_expr: Optional[str]) -> Any:
    """
    Extract desired result from raw task output using ResultExpr.
    """
    return evaluate_expr(result_data, result_expr)


def apply_output_expr(output_data: Any, output_expr: Optional[str]) -> Any:
    """
    Final output shaping for passing to the next state.
    """
    return evaluate_expr(output_data, output_expr)
