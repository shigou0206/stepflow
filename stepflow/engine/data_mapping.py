# data_mapping.py
from typing import Dict, Any, Union
import jsonata

#######################
# Nested path helpers
#######################
def get_nested(data: Dict[str, Any], path: str) -> Any:
    if not path:
        return data
    keys = path.split(".")
    current = data
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
    return current

def set_nested(data: Dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    current = data
    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value

#######################
# 1) extract_input
#######################
def extract_input(context: Dict[str, Any], input_path: str) -> Dict[str, Any]:
    """
    1) 从 context 中获取 input_path 指定的数据
    2) 如果 path 未指定, 默认返回整个上下文
    3) 如果 path 不存在, 返回 {}
    """
    if not input_path or not input_path.startswith("$."):
        return context
    path_key = input_path[2:]  # 去掉 "$."
    sub_data = get_nested(context, path_key)
    if sub_data is None:
        return {}
    if not isinstance(sub_data, dict):
        # 包成 dict
        return {"value": sub_data}
    return sub_data

#######################
# 2) build_parameters
#######################
def build_parameters(input_data: Dict[str, Any], params_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    1) 如果 key.endswith(".$"): dynamic path => val is a path
    2) 如果 key.endswith(".#jsonata"): run jsonata
    3) else => static
    """
    final = {}
    for key, val in params_def.items():
        if key.endswith(".$"):
            # dynamic path
            real_key = key[:-2]
            if isinstance(val, str) and val.startswith("$."):
                # 取 input_data 里的那部分
                sub_key = val[2:]
                res = get_nested(input_data, sub_key)
                final[real_key] = res
            else:
                raise ValueError(f"Invalid param path: {val}")

        elif key.endswith(".#jsonata"):
            # JSONATA
            real_key = key[:-8]
            if isinstance(val, str):
                expr = jsonata.compile(val)
                result = expr.evaluate(input_data)
                final[real_key] = result
            else:
                raise ValueError(f"Jsonata expr must be a string, got: {val}")

        else:
            # static
            final[key] = val
    return final

#######################
# 3) merge_result
#######################
def merge_result(context: Dict[str, Any], output: Any, result_path: str) -> None:
    """
    将节点输出放回 context 的 result_path (若有).
    如果 result_path 不存在, 合并到根上下文.
    """
    if not result_path or not result_path.startswith("$."):
        # 合并到根
        if isinstance(output, dict):
            context.update(output)
        else:
            context["result"] = output
        return

    path_key = result_path[2:]
    # set_nested  (若要覆盖多层)
    set_nested(context, path_key, output)

#######################
# 4) filter_output
#######################
def filter_output(context: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    根据 output_path 决定返回给下一个状态的数据.
    如果 output_path 未指定, 返回整个 context.
    如果 output_path 是多层, get_nested.
    """
    if not output_path or not output_path.startswith("$."):
        return context
    path_key = output_path[2:]
    data = get_nested(context, path_key)
    if data is None:
        return {}
    if not isinstance(data, dict):
        return {"value": data}
    return data

#######################
# 5) merge_aggregator
#######################
def merge_aggregator(context: Dict[str, Any], new_output: Any, merge_mode: str, merge_path: str) -> None:
    """
    将新的执行结果聚合到 merge_path 位置, 根据 merge_mode 不同:
      - overwrite: 直接覆盖
      - append: 在 list 后追加
      - dictIndex: 在 dict 里按 run index/timestamp 存放
      - custom: 可调用可插拔函数
    """
    if not merge_path or not merge_path.startswith("$."):
        # 未指定, 则什么都不做
        return

    path_key = merge_path[2:]
    existing = get_nested(context, path_key)

    if merge_mode == "overwrite":
        set_nested(context, path_key, new_output)

    elif merge_mode == "append":
        # 把 existing 当做 list
        if not isinstance(existing, list):
            # 若 existing是None/非list => 变成list
            if existing is None:
                existing = []
            else:
                existing = [existing]
        existing.append(new_output)
        set_nested(context, path_key, existing)

    elif merge_mode == "dictIndex":
        # 用一个自增 index 作为 key
        if not isinstance(existing, dict):
            existing = {}
        run_index = existing.get("__run_index__", 0)
        existing[f"run_{run_index}"] = new_output
        existing["__run_index__"] = run_index + 1
        set_nested(context, path_key, existing)

    elif merge_mode == "custom":
        # 这里可调用外部自定义函数
        # e.g. from stepflow.plugins.merge_funcs import custom_merge
        # new_data = custom_merge(existing, new_output)
        # set_nested(context, path_key, new_data)
        pass

    else:
        # 若不识别, 也就 overwrite
        set_nested(context, path_key, new_output)