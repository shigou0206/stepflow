# stepflow/states/succeed_state.py
def execute_succeed(state_def: dict, context: dict) -> str:
    # 返回 None 代表结束
    return None