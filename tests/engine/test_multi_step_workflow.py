
import pytest
from stepflow.dsl.dsl_model import WorkflowDSL
from stepflow.hooks.base import ExecutionHooks
from stepflow.worker.tools.tool_registry import tool_registry
from stepflow.worker.tools.http_tool import HttpTool
from stepflow.worker.tools.shell_tool import ShellTool
from stepflow.engine.workflow_engine import WorkflowEngine


class PrintHook(ExecutionHooks):
    async def on_workflow_start(self, run_id: str):
        print(f"[{run_id}] 🚀 Workflow started")

    async def on_node_enter(self, run_id: str, state_id: str, input_data):
        print(f"[{run_id}] ▶️ Entering {state_id} with input: {input_data}")

    async def on_node_success(self, run_id: str, state_id: str, output_data):
        print(f"[{run_id}] ✅ {state_id} succeeded, output: {output_data}")

    async def on_node_fail(self, run_id: str, state_id: str, error: str):
        print(f"[{run_id}] ❌ {state_id} failed: {error}")

    async def on_workflow_end(self, run_id: str, result):
        print(f"[{run_id}] 🏁 Workflow ended with result: {result}")

    async def on_control_signal(self, run_id: str, signal: str, reason: str):
        print(f"[{run_id}] ⚠️ Control signal: {signal}, reason: {reason}")


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

    engine = WorkflowEngine(hook=PrintHook())
    result = await engine.run("multi-step-run", dsl, {})
    assert "Final step" in result
