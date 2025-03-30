# stepflow/domain/engine/path_utils.py
# 简化的 get_value_by_path / set_value_by_path，用于 InputPath/ResultPath/OutputPath
import copy
from typing import Any

def get_value_by_path(data: dict, path: str) -> Any:
    if path == "$":
        return data
    path_keys = path.lstrip("$.").split(".")
    current = data
    for k in path_keys:
        if not k:
            continue
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None
    return current

def set_value_by_path(data: dict, path: str, value: Any) -> dict:
    if path == "$":
        return value if isinstance(value, dict) else {"value": value}
    path_keys = path.lstrip("$.").split(".")
    current = data
    for i, k in enumerate(path_keys):
        if not k:
            continue
        if i == len(path_keys) - 1:
            current[k] = value
        else:
            if k not in current:
                current[k] = {}
            current = current[k]
            if not isinstance(current, dict):
                raise ValueError(f"Cannot set path {path}, intermediate {k} is not dict")
    return data