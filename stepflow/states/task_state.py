# task_state.py
from stepflow.engine.data_mapping import (
    extract_input, build_parameters, merge_result, filter_output, merge_aggregator
)

def execute_task(state_def: dict, context: dict) -> str:
    from stepflow.engine.dispatcher import run_resource
    # 1. InputPath -> input_data
    input_data = extract_input(context, state_def.get("InputPath"))

    # 2. Parameters
    params = build_parameters(input_data, state_def.get("Parameters", {}))

    # 3. 执行资源
    resource_name = state_def["Resource"]
    output = run_resource(resource_name, params, context)

    # 4. 先把本次输出写入 resultPath
    merge_result(context, output, state_def.get("ResultPath"))

    # 5. 如果 DSL 中指定 MergeMode != None, 则做聚合
    merge_mode = state_def.get("MergeMode", "overwrite")  
    merge_path = state_def.get("MergePath", "")          
    if merge_mode != "overwrite":
        # 取到 output, aggregator
        new_output = output  # or the entire result?
        # 这里你也可先从 resultPath 取 output (context[state_def["ResultPath"][2:]]) 
        merge_aggregator(context, new_output, merge_mode, merge_path)

    # 6. OutputPath -> next_context
    next_context = filter_output(context, state_def.get("OutputPath"))

    # 7. 覆盖 global context, 以保证下一个状态只能看到 next_context
    context.clear()
    context.update(next_context)

    # 8. 返回 Next
    return state_def.get("Next")