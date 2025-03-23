# stepflow/states/choice_state.py

def execute_choice(state_def: dict, context: dict) -> str:
    """
    读取 state_def["Choices"] 数组，逐个判断:
      - if "NumericLessThan": variable值 < ...
      - if "StringEquals": variable值 == ...
      - etc.
    如果匹配, 返回 choice["Next"]
    如果都没匹配, 返回 state_def["Default"]
    """
    choices = state_def.get("Choices", [])
    default_next = state_def.get("Default")

    for choice in choices:
        var_path = choice["Variable"]  # e.g. "$.counter"
        # 你还可能有 StringEquals, NumericLessThan, ...
        # 先从 context 里拿这个 var_path
        variable_key = var_path[2:] if var_path.startswith("$.") else var_path
        actual_value = context.get(variable_key)

        if "NumericLessThan" in choice:
            if isinstance(actual_value, (int, float)) and actual_value < choice["NumericLessThan"]:
                return choice["Next"]

        if "StringEquals" in choice:
            if isinstance(actual_value, str) and actual_value == choice["StringEquals"]:
                return choice["Next"]
        
        # 你也可以加更多 Operators: NumericGreaterThan, etc.

    # 如果都没匹配, 看有没有 Default
    if default_next:
        return default_next

    # 如果没有 Default, 可以报错 or return None
    raise Exception("Choice state has no matching branch and no Default")