
import pytest
from stepflow.dsl.dsl_model import WorkflowDSL
from stepflow.hooks.base import ExecutionHooks
from stepflow.worker.tools.tool_registry import tool_registry
from stepflow.worker.tools.http_tool import HttpTool
from stepflow.worker.tools.shell_tool import ShellTool
from stepflow.engine.workflow_engine import WorkflowEngine
from stepflow.tests.mocks.execution_service import MockExecutionService
from stepflow.tests.mocks.task_service import MockTaskService
from stepflow.hooks.print_hook import PrintHook


@pytest.mark.asyncio
async def test_multi_step_workflow():
    tool_registry["HttpTool"] = HttpTool()
    tool_registry["ShellTool"] = ShellTool()

    dsl = WorkflowDSL.model_validate({
        "StartAt": "StepA",
        "States": {
            "StepA": {
                "Type": "Task",
                "Resource": "HttpTool",
                "Parameters": {
                    "url": "https://httpbin.org/get",
                    "method": "GET",
                    "parse_json": True
                },
                "ResultExpr": "$.json.url",
                "OutputExpr": "$",
                "Next": "StepB"
            },
            "StepB": {
                "Type": "Pass",
                "InputExpr": "$",
                "Result": "Preparing to execute",
                "ResultPath": "$.message",
                "OutputExpr": "$",
                "Next": "StepC"
            },
            "StepC": {
                "Type": "Task",
                "Resource": "ShellTool",
                "Parameters": {
                    "command": "echo 'Final step'",
                    "timeout": 5
                },
                "ResultExpr": "$.stdout",
                "End": True
            }
        }
    })

    engine = WorkflowEngine(hook=PrintHook(), execution_service=MockExecutionService(), task_service=MockTaskService())
    result = await engine.run("multi-step-run", dsl, {})
    assert "Final step" in result
