from typing import Dict, Any

def extract_input(context: Dict[str, Any], input_path: str) -> Dict[str, Any]:
    """
    1) 从 context 中获取 input_path 指定的数据
    2) 如果 path 未指定, 默认返回整个上下文
    3) 如果 path 不存在, 返回空或 {}
    """
    if not input_path or not input_path.startswith("$."):
        return context
    path_key = input_path[2:]  # 去掉 "$."
    sub_data = context.get(path_key, {})
    # 若是原子值, 也可把它包装成 dict
    if not isinstance(sub_data, dict):
        return {"value": sub_data}
    return sub_data


def build_parameters(input_data: Dict[str, Any], params_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    1) 支持 foo.$: "$.someField" 的路径引用
    2) 否则当做静态值
    """
    final = {}
    for key, val in params_def.items():
        if key.endswith(".$"):
            real_key = key[:-2]
            if isinstance(val, str) and val.startswith("$."):
                sub_key = val[2:]
                final[real_key] = input_data.get(sub_key)
            else:
                raise ValueError(f"Invalid param path: {val}")
        else:
            final[key] = val
    return final


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
    context[path_key] = output


def filter_output(context: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    根据 output_path 决定返回给下一个状态的数据.
    如果 output_path 未指定, 返回整个 context.
    如果 output_path 指向一个具体字段, 只返回那部分.
    """
    if not output_path or not output_path.startswith("$."):
        return context
    path_key = output_path[2:].split(".")
    data = context
    for key in path_key:
        if isinstance(data, dict) and (key in data):
            data = data[key]
        else:
            return {}
    # 如果 data 不是 dict, 可包成 {"value": data} 或 {path_key[-1]: data}
    if not isinstance(data, dict):
        return {"value": data}
    return data


def merge_aggregator(context: Dict[str, Any], new_output: Any, merge_mode: str, merge_path: str) -> None:
    """
    将新的执行结果聚合到 merge_path 位置, 根据 merge_mode 不同:
      - overwrite: 直接覆盖
      - append: 在 list 后追加
      - dictIndex: 在 dict 里按 run index/timestamp 存放
      - custom: 可调用可插拔函数
    """
    if not merge_path or not merge_path.startswith("$."):
        # 未指定, 则默认为根?
        return

    path_key = merge_path[2:]
    existing = context.get(path_key)

    if merge_mode == "overwrite":
        # 就直接覆盖
        context[path_key] = new_output

    elif merge_mode == "append":
        # 把 existing 当做 list
        if not isinstance(existing, list):
            existing = [] if existing is None else [existing]
        existing.append(new_output)
        context[path_key] = existing

    elif merge_mode == "dictIndex":
        # 用一个自增 index 作为 key
        if not isinstance(existing, dict):
            existing = {}
        run_index = existing.get("__run_index__", 0)
        existing[f"run_{run_index}"] = new_output
        existing["__run_index__"] = run_index + 1
        context[path_key] = existing

    elif merge_mode == "custom":
        # 这里可调用外部自定义函数
        # e.g. from stepflow.plugins.merge_funcs import custom_merge
        # custom_merge(existing, new_output)
        pass

    else:
        # 若不识别, 也就 overwrite
        context[path_key] = new_output