# stepflow/engine/dispatcher.py
from stepflow.states.pass_state import execute_pass
from stepflow.states.task_state import execute_task
from stepflow.states.succeed_state import execute_succeed
from stepflow.states.fail_state import execute_fail
from stepflow.states.choice_state import execute_choice
# 将状态类型映射到具体执行函数
STATE_EXECUTORS = {
    "Pass": execute_pass,
    "Task": execute_task,
    "Succeed": execute_succeed,
    "Fail": execute_fail,
    "Choice": execute_choice,
}

def get_state_executor(state_type: str):
    if state_type not in STATE_EXECUTORS:
        raise Exception(f"Unsupported state type: {state_type}")
    return STATE_EXECUTORS[state_type]


# 资源节点注册表（示例）
from stepflow.resources.shell_exec import run as shell_exec_run

RESOURCE_REGISTRY = {
    "shell.exec": shell_exec_run
}

def run_resource(resource_name: str, params: dict, context: dict):
    if resource_name not in RESOURCE_REGISTRY:
        raise Exception(f"Unknown resource: {resource_name}")
    return RESOURCE_REGISTRY[resource_name](params, context)