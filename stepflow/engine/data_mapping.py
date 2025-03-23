# stepflow/engine/data_mapping.py
def build_input(context: dict, state_def: dict) -> dict:
    """
    示例: 直接返回 state_def['Parameters'].
    若想支持 InputPath、Parameters.$、ResultPath 等, 可以在此实现.
    """
    return state_def.get("Parameters", {})

def apply_result(context: dict, result: dict, state_def: dict):
    """
    如果你想把 result 合并回 context, 并支持 ResultPath, 可以在此实现.
    """
    context.update(result)  # 简单示例