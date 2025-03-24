# stepflow/states/task_state.py
from typing import Dict, Any
from stepflow.engine.context import WorkflowContext
from stepflow.engine.data_mapping import (
    extract_input, build_parameters, merge_result, merge_aggregator, filter_output
)
from stepflow.engine.task_executor import ITaskExecutor

def execute_task(state_def: Dict[str, Any],
                 context: WorkflowContext,
                 task_executor: ITaskExecutor) -> str:
    """
    1) 提取input
    2) build_parameters => 解析 static/dynamic/jsonata
    3) 执行Task
    4) resultPath/mergeMode
    5) outputPath
    6) 更新context
    7) 返回Next
    """
    # 1) input_data
    input_data: Dict[str, Any] = extract_input(context.to_dict(), state_def.get("InputPath"))

    # 2) build_parameters => 这里面可以对 "xxx.#jsonata" 做 special handle
    final_params: Dict[str, Any] = build_parameters(input_data, state_def.get("Parameters", {}))

    # 3) execute
    resource_name: str = state_def["Resource"]
    output: Any = task_executor.execute_task(resource_name, final_params)

    # 4) resultPath
    merge_result(context.to_dict(), output, state_def.get("ResultPath"))
    # 你可能需要写回 context.set_data(...). (取决于 data_flow设计)

    # 5) merge aggregator
    merge_mode: str = state_def.get("MergeMode", "overwrite")
    merge_path: str = state_def.get("MergePath", "")
    if merge_mode != "overwrite":
        new_output: Any = output
        merge_aggregator(context.to_dict(), new_output, merge_mode, merge_path)
        # 同理: sync back to context ?

    # 6) outputPath
    next_context: Dict[str, Any] = filter_output(context.to_dict(), state_def.get("OutputPath"))
    context.data.clear()
    context.data.update(next_context)

    # 7) next
    next_state: str = state_def.get("Next", "")
    return next_state