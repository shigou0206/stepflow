# stepflow/utils/io_utils.py

def extract_data(context: dict, path: str):
    # 如果你想实现真正的 JSON Path，这里可以做更复杂的解析
    if not path or not path.startswith("$."):
        return context
    key = path[2:]
    return context.get(key)

def merge_data(context: dict, data: dict, path: str):
    if not path or not path.startswith("$."):
        context.update(data)
    else:
        key = path[2:]
        context[key] = data
    return context