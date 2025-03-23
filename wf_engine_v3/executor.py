# executor.py
import asyncio
import json
import hashlib
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from .workflow import Workflow, WorkflowNode
from .nodes import node_types_map

logger = logging.getLogger("workflow_executor")

# 无限循环检测器：基于节点ID和输入数据生成状态hash
class InfiniteLoopDetector:
    def __init__(self, max_occurrences: int = 3):
        self.state_counter = defaultdict(int)
        self.max_occurrences = max_occurrences

    def get_state_hash(self, node_id: str, input_data: Dict[str, Any]) -> str:
        data_str = json.dumps(input_data, sort_keys=True)
        state_str = f"{node_id}-{data_str}"
        return hashlib.md5(state_str.encode()).hexdigest()

    def check_infinite_loop(self, node_id: str, input_data: Dict[str, Any]) -> bool:
        state_hash = self.get_state_hash(node_id, input_data)
        self.state_counter[state_hash] += 1
        return self.state_counter[state_hash] > self.max_occurrences

# 错误处理器
class ErrorHandler:
    def __init__(self, default_max_retries: int = 3, default_retry_interval: float = 1.0):
        self.default_max_retries = default_max_retries
        self.default_retry_interval = default_retry_interval

    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[List[List[Dict[str, Any]]]]],
        max_retries: Optional[int] = None,
        retry_interval: Optional[float] = None,
    ) -> List[List[Dict[str, Any]]]:
        max_r = max_retries if max_retries is not None else self.default_max_retries
        interval = retry_interval if retry_interval is not None else self.default_retry_interval
        for attempt in range(1, max_r + 1):
            try:
                return await func()
            except Exception as e:
                logger.error("Error on attempt %d: %s", attempt, e)
                if attempt < max_r:
                    await asyncio.sleep(interval)
                else:
                    raise e

# 节点执行器
class NodeExecutor:
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler

    async def execute_node(self, node: WorkflowNode, inputs: Dict[str, Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        node_type = node_types_map.get(node.type)
        if not node_type:
            raise ValueError(f"Unsupported node type: {node.type}") 
        async def _execute():
            return await node_type.execute(inputs)
        if node.retry_on_fail:
            return await self.error_handler.execute_with_retry(
                _execute, max_retries=node.max_tries, retry_interval=node.wait_between_tries
            )
        else:
            return await _execute()

# 结果汇总器
class ResultAggregator:
    def __init__(self):
        self.node_execution_order: List[str] = []
        self.node_data: Dict[str, List[Any]] = {}

    def record_result(self, node_name: str, result: List[List[Dict[str, Any]]]) -> None:
        self.node_execution_order.append(node_name)
        self.node_data.setdefault(node_name, []).append(result)
        logger.debug("Recorded result for node %s: %s", node_name, result)

    def finalize(self, start_time: datetime, status: str, error: Optional[Exception] = None) -> Dict[str, Any]:
        stop_time = datetime.utcnow()
        return {
            "status": status,
            "start_time": start_time.isoformat(),
            "stop_time": stop_time.isoformat(),
            "nodeExecutionOrder": self.node_execution_order,
            "nodeData": self.node_data,
            "error": str(error) if error else None,
        }

# 工作流执行器
class WorkflowExecutor:
    """
    工作流执行器：
      - 对于预期输入数大于1的节点，通过 pending_inputs 聚合同一节点所有输入后再执行；
      - 每次执行前检查无限循环状态；
      - 调度下游任务时，对于 Merge 和 If 节点保持二维数组格式，其它节点取 result[0][0]。
    """
    def __init__(self, workflow: Workflow, additional_context: Optional[Dict[str, Any]] = None):
        self.workflow = workflow
        self.additional_context = additional_context or {}
        self.error_handler = ErrorHandler()
        self.node_executor = NodeExecutor(self.error_handler)
        # 使用列表作为任务栈（LIFO 调度）
        self.scheduler: List[Tuple[str, str, Dict[str, Any]]] = []
        self.result_aggregator = ResultAggregator()
        self.status: str = "new"
        self.execution_error: Optional[Exception] = None
        self.pending_inputs: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self.loop_detector = InfiniteLoopDetector(max_occurrences=3)

    def add_task(self, node_name: str, input_source: str, input_data: Dict[str, Any]) -> None:
        node = self.workflow.nodes.get(node_name)
        if node and node.type == "nodes-base.merge":
            if node.parameters.get("mode") == "passThrough" and not input_data:
                logger.debug("Skipping task for Merge node '%s' with empty input", node_name)
                return
        self.scheduler.append((node_name, input_source, input_data))
        logger.debug("Added task: %s, %s, %s", node_name, input_source, input_data)

    def get_child_tasks(self, node_name: str, result: List[List[Dict[str, Any]]]) -> List[Tuple[str, str, Dict[str, Any]]]:
        tasks = []
        for conn in self.workflow.get_child_connections(node_name):
            next_node = conn.target
            child_node = self.workflow.nodes.get(next_node)
            source = f"input{conn.index + 1}"
            if child_node and child_node.type in ["nodes-base.merge", "nodes-base.if"]:
                input_data = result
            else:
                input_data = result[0][0] if result and result[0] else {}
            tasks.append((next_node, source, input_data))
        return tasks

    async def run(self) -> Dict[str, Any]:
        start_time = datetime.utcnow()
        start_node = self.workflow.get_start_node()
        if start_node is None:
            raise Exception("No start node found for the workflow.")
        self.status = "running"
        self.add_task(start_node.name, "input1", {})

        while self.scheduler:
            node_name, input_source, input_data = self.scheduler.pop()
            node = self.workflow.nodes.get(node_name)
            if node is None or node.disabled:
                continue

            expected_count = self.workflow.expected_input_count(node_name)
            if expected_count > 1:
                self.pending_inputs[node_name][input_source] = input_data
                if len(self.pending_inputs[node_name]) < expected_count:
                    logger.debug("Waiting for more inputs for node '%s' (got %d, expected %d)",
                                 node_name, len(self.pending_inputs[node_name]), expected_count)
                    continue
                inputs_for_exec = dict(self.pending_inputs[node_name])
                del self.pending_inputs[node_name]
            else:
                inputs_for_exec = {input_source: input_data}

            # 检查无限循环
            state_hash = self.loop_detector.get_state_hash(node.id, inputs_for_exec.get("input1", {}))
            if self.loop_detector.check_infinite_loop(node.id, inputs_for_exec.get("input1", {})):
                error_msg = f"Infinite loop detected on node '{node.name}'"
                logger.error(error_msg)
                self.result_aggregator.record_result(node.name, [[{"error": error_msg}]])
                self.status = "error"
                break

            logger.debug("Executing node '%s' with inputs: %s", node.name, inputs_for_exec)
            try:
                result = await self.node_executor.execute_node(node, inputs_for_exec)
            except Exception as e:
                self.execution_error = e
                logger.error("Error executing node '%s': %s", node.name, e)
                if not node.continue_on_fail:
                    self.status = "error"
                    self.result_aggregator.record_result(node.name, [[{"error": str(e)}]])
                    break
                result = [[{"error": str(e)}]]
                self.status = "error"
            self.result_aggregator.record_result(node.name, result)
            for task in self.get_child_tasks(node.name, result):
                self.add_task(*task)

        if self.status != "error":
            self.status = "success"
        return self.result_aggregator.finalize(start_time, self.status, self.execution_error)