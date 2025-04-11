# stepflow/domain/engine/path_utils.py
# 简化的 get_value_by_path / set_value_by_path，用于 InputPath/ResultPath/OutputPath
import copy
import re
import json
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

def get_value_by_path(data: dict, path: str) -> Any:
    """
    根据路径获取数据中的值
    
    Args:
        data: 要查询的数据字典
        path: 路径，例如 "$.user.name"
    
    Returns:
        路径对应的值，如果路径不存在则返回 None
    """
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
    """
    根据路径设置数据中的值
    
    Args:
        data: 要修改的数据字典
        path: 路径，例如 "$.user.name"
        value: 要设置的值
    
    Returns:
        修改后的数据字典
    """
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

def resolve_path_references(text: str, data: dict) -> str:
    """
    解析文本中的路径引用，例如 "Hello, $.user.name!"
    
    Args:
        text: 包含路径引用的文本
        data: 数据字典
    
    Returns:
        解析后的文本
    """
    if not text or not isinstance(text, str) or "$." not in text:
        return text
    
    try:
        # 使用正则表达式查找所有路径引用
        pattern = r'\$\.[a-zA-Z0-9_.]+' 
        
        def replace_path(match):
            path = match.group(0)
            value = get_value_by_path(data, path)
            
            # 如果值是字典或列表，转换为 JSON 字符串
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            
            # 如果值是 None，返回空字符串
            if value is None:
                return ""
            
            # 否则，返回字符串形式的值
            return str(value)
        
        # 替换所有路径引用
        result = re.sub(pattern, replace_path, text)
        return result
    except Exception as e:
        logger.error(f"解析路径引用时出错: {str(e)}")
        return text

def merge_with_path_references(template: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并模板和数据，解析模板中的路径引用
    
    Args:
        template: 包含路径引用的模板
        data: 数据字典
    
    Returns:
        合并后的字典
    """
    if not template:
        return {}
    
    try:
        result = {}
        
        for key, value in template.items():
            if isinstance(value, str) and "$." in value:
                # 如果值是包含路径引用的字符串，解析它
                result[key] = resolve_path_references(value, data)
            elif isinstance(value, dict):
                # 如果值是字典，递归处理
                result[key] = merge_with_path_references(value, data)
            elif isinstance(value, list):
                # 如果值是列表，处理列表中的每个元素
                result[key] = [
                    merge_with_path_references(item, data) if isinstance(item, dict)
                    else resolve_path_references(item, data) if isinstance(item, str) and "$." in item
                    else item
                    for item in value
                ]
            else:
                # 其他情况，直接复制值
                result[key] = value
        
        return result
    except Exception as e:
        logger.error(f"合并路径引用时出错: {str(e)}")
        return template