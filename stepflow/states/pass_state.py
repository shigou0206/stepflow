# stepflow/states/pass_state.py
def execute_pass(state_def: dict, context: dict) -> str:
    # 如果有 "Result", 可以把它 merge 到上下文
    result = state_def.get("Result", {})
    context.update(result)
    return state_def.get("Next")