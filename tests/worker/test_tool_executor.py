
import pytest
import asyncio
from stepflow.worker.task_executor import TaskExecutor
from stepflow.dsl.dsl_model import TaskState
from stepflow.worker.tools.tool_registry import tool_registry


@pytest.mark.asyncio
async def test_http_tool_get():
    state = TaskState(
        type="Task",
        resource="HttpTool",
        parameters={
            "url": "https://httpbin.org/get",
            "method": "GET",
            "parse_json": True
        },
        result_expr="$.json.url",
        end=True
    )
    executor = TaskExecutor()
    output = await executor.run_task(state, input_data={})
    assert "httpbin.org" in output


# @pytest.mark.asyncio
# async def test_shell_tool_ls():
#     state = TaskState(
#         type="Task",
#         resource="ShellTool",
#         parameters={
#             "command": "ls",
#             "timeout": 5
#         },
#         result_expr="$.stdout",
#         end=True
#     )
#     executor = TaskExecutor()
#     output = executor.run_task(state, input_data={})
#     assert isinstance(output, str)
#     assert len(output) > 0
