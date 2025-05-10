import pytest
from stepflow.worker.task_executor import TaskExecutor
from stepflow.dsl.dsl_model import TaskState
from stepflow.worker.tools.tool_registry import tool_registry


class DummyTool:
    def execute(self, input_data):
        return {"output": input_data.get("x", 0) + 1}


def setup_dummy():
    tool_registry["DummyTool"] = DummyTool()


def test_run_task_basic():
    setup_dummy()
    state = TaskState(
        type="Task",
        resource="DummyTool",
        parameters={"x": 41},
        input_expr=None,
        result_expr="$.status",
        output_expr=None,
        end=True
    )
    executor = TaskExecutor()
    output = executor.run_task(state, input_data={})
    assert output == 42