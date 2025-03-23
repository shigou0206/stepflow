# stepflow/states/task_state.py
from stepflow.engine.data_mapping import build_input, apply_result

def execute_task(state_def: dict, context: dict) -> str:
    # Import the function locally to avoid circular imports
    from stepflow.engine.dispatcher import run_resource
    
    # 准备节点输入 (Parameters)
    params = build_input(context, state_def)

    resource = state_def["Resource"]
    # 调用资源节点
    output = run_resource(resource, params, context)

    # 合并结果
    apply_result(context, output, state_def)

    return state_def.get("Next")