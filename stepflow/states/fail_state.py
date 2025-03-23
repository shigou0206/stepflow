# stepflow/states/fail_state.py
def execute_fail(state_def: dict, context: dict) -> str:
    cause = state_def.get("Cause", "Unknown cause")
    raise Exception(f"FailState: {cause}")