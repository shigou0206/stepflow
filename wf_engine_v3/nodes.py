# nodes.py
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List
from .model import NodeType

from asteval import Interpreter

logger = logging.getLogger("workflow_executor")

# Start 节点：返回二维数组格式的 [{}]
@dataclass
class StartNode(NodeType):
    async def execute(self, inputs: Dict[str, Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        logger.debug("Executing Start node '%s'", self.name)
        return [[{}]]

# Set 节点：更新输入数据，支持表达式计算
@dataclass
class SetNode(NodeType):
    interpreter: Interpreter = field(default_factory=Interpreter)

    async def execute(self, inputs: Dict[str, Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        logger.debug("Executing Set node '%s'", self.name)
        base = inputs.get("input1", {}).copy()
        values = self.parameters.get("values", {}).get("number", [])
        result = base.copy()
        for entry in values:
            name = entry["name"]
            expr = entry["value"]
            result[name] = self.evaluate_expression(expr, inputs)
        return [[result]]

    def evaluate_expression(self, expr: Any, inputs: Dict[str, Dict[str, Any]]) -> Any:
        if isinstance(expr, str) and expr.startswith("={{") and expr.endswith("}}"):
            expr_str = expr[3:-2].strip()
            # 将 $input.first() 替换为合法函数调用 input_first()
            expr_str = expr_str.replace("$input.first()", "input_first()")
            # 设置上下文：input_first 返回 input1 的数据（直接返回字典）
            context = {
                "input_first": lambda: inputs.get("input1", {})
            }
            self.interpreter.symtable.update(context)
            try:
                return self.interpreter(expr_str)
            except Exception as e:
                logger.error("Expression evaluation error in node '%s': %s", self.name, e)
                return None
        return expr

# Merge 节点：支持 mergeByIndex 和 passThrough 模式
@dataclass
class MergeNode(NodeType):
    async def execute(self, inputs: Dict[str, Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        logger.debug("Executing Merge node '%s'", self.name)
        mode = self.parameters.get("mode", "mergeByIndex")
        output_choice = self.parameters.get("output", "input1")
        if mode == "passThrough":
            chosen = inputs.get(output_choice, {})
            logger.debug("Merge passThrough from %s: %s", output_choice, chosen)
            if isinstance(chosen, list):
                return chosen
            else:
                return [[chosen]]
        elif mode == "mergeByIndex":
            merged_list = []
            for key in sorted(inputs.keys()):
                data = inputs[key]
                if isinstance(data, list) and data and isinstance(data[0], list) and data[0]:
                    merged_list.append(data[0][0])
                else:
                    merged_list.append(data)
            logger.debug("Merge mergeByIndex result (list): %s", merged_list)
            return [merged_list]
        else:
            raise ValueError(f"Unsupported merge mode: {mode}")

# If 节点：根据条件返回二维数组 [true_branch, false_branch]
@dataclass
class IfNode(NodeType):
    async def execute(self, inputs: Dict[str, Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        logger.debug("Executing IF node '%s'", self.name)
        conditions = self.parameters.get("conditions", {}).get("number", [])
        input_data_raw = inputs.get("input1", {})
        if isinstance(input_data_raw, list) and input_data_raw and isinstance(input_data_raw[0], list):
            input_data = input_data_raw[0][0]
        else:
            input_data = input_data_raw
        condition = conditions[0] if conditions else {}
        val1_expr = condition.get("value1", "")
        val2 = condition.get("value2")
        val1 = self.evaluate_expression(val1_expr, input_data)
        if val1 == val2:
            return [[input_data], []]
        else:
            return [[], [input_data]]

    def evaluate_expression(self, expr: str, input_data: Dict[str, Any]) -> Any:
        if isinstance(expr, str) and expr.startswith("={{") and expr.endswith("}}"):
            expr_str = expr[3:-2].strip()
            if expr_str.startswith("$json."):
                key = expr_str[len("$json."):].strip()
                return input_data.get(key)
        return None

# Wait 节点：延时等待后传递输入数据
@dataclass
class WaitNode(NodeType):
    async def execute(self, inputs: Dict[str, Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        wait_time = self.parameters.get("wait", 1)
        logger.debug("Executing Wait node '%s', waiting for %s seconds", self.name, wait_time)
        await asyncio.sleep(wait_time)
        return [[inputs.get("input1", {})]]
    
node_types_map = {
    "nodes-base.start": StartNode(),
    "nodes-base.set": SetNode(),
    "nodes-base.merge": MergeNode(),
    "nodes-base.if": IfNode(),
    "nodes-base.wait": WaitNode()
}