from stepflow.dsl.dsl_model import TaskState
from stepflow.worker.tools.tool_registry import tool_registry
from stepflow.expression.parameter_mapper import (
    apply_parameters,
    apply_result_expr,
    apply_output_expr,
)
from typing import Dict, Any


class TaskExecutor:
    async def run_task(self, state: TaskState, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Step 1: 参数映射
        task_input = apply_parameters(input_data, state.parameters, input_expr=state.input_expr)

        # Step 2: 执行任务（同步）
        print(f"Executing task with resource: {state.resource}")
        print(f"Task input: {task_input}")
        tool = tool_registry.get(state.resource)
        print(f"Tool: {tool}")
        if not tool:
            raise ValueError(f"Unknown tool type: {state.resource}")
        raw_result = await tool.execute(task_input)
        print(f"Raw result: {raw_result}")
        # Step 3: 输出结果映射
        intermediate = apply_result_expr(raw_result, state.result_expr)
        print(f"Intermediate: {intermediate}")
        output_data = apply_output_expr(intermediate, state.output_expr)
        print(f"Output data: {output_data}")
        return output_data