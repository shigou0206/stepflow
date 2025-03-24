# stepflow/engine/context.py

from typing import Dict, Any, Optional
import copy
import jsonata   # pip install jsonata

class WorkflowContext:
    """
    一个带类型注解的上下文类, 同时支持 Jsonata 运算
    """

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        self.data: Dict[str, Any] = data or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        返回上下文数据 (做深拷贝保护).
        """
        return copy.deepcopy(self.data)

    def get_path(self, path: str) -> Any:
        """
        e.g. path = "$.foo.bar"
        自行实现多层嵌套访问
        """
        if path.startswith("$."):
            path = path[2:]
        if not path:
            return self.data
        keys = path.split(".")
        current = self.data
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
        return current

    def set_path(self, path: str, value: Any) -> None:
        """
        e.g. path = "$.foo.bar"
        下钻创建多层
        """
        if path.startswith("$."):
            path = path[2:]
        if not path:
            # 直接替换data
            if isinstance(value, dict):
                self.data = value
            else:
                self.data = {}
            return
        keys = path.split(".")
        current = self.data
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def evaluate_jsonata(self, expr_str: str) -> Any:
        """
        用 jsonata.compile(expr_str) 对 self.data 做复杂过滤/运算, 返回结果(不改self.data)
        """
        expr = jsonata.compile(expr_str)
        result = expr.evaluate(self.data)
        return result