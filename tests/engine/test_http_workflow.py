
import pytest
from typing import Optional
from stepflow.dsl.dsl_model import WorkflowDSL
from stepflow.hooks.base import ExecutionHooks
from stepflow.worker.task_executor import TaskExecutor
from stepflow.worker.tools.tool_registry import tool_registry
from stepflow.worker.tools.http_tool import HttpTool
from stepflow.engine.workflow_engine import WorkflowEngine


class PrintHook(ExecutionHooks):
    async def on_workflow_start(self, run_id: str):
        print(f"[{run_id}] 🚀 Workflow started")

    async def on_node_enter(self, run_id: str, state_id: str, input_data):
        print(f"[{run_id}] ▶️ Entering {state_id} with {input_data}")

    async def on_node_success(self, run_id: str, state_id: str, output_data):
        print(f"[{run_id}] ✅ {state_id} succeeded with {output_data}")

    async def on_node_fail(self, run_id: str, state_id: str, error: str):
        print(f"[{run_id}] ❌ {state_id} failed: {error}")

    async def on_workflow_end(self, run_id: str, result):
        print(f"[{run_id}] 🏁 Workflow ended with result: {result}")

    async def on_control_signal(self, run_id: str, signal: str, reason: Optional[str]):
        print(f"[{run_id}] ⚠️ Control signal: {signal} ({reason})")


@pytest.mark.asyncio
async def test_http_workflow():
    tool_registry["HttpTool"] = HttpTool()

    dsl = WorkflowDSL.model_validate({
        "StartAt": "FetchData",
        "States": {
            "FetchData": {
                "Type": "Task",
                "Resource": "HttpTool",
                "Parameters": {
                    "url": "https://httpbin.org/get",
                    "method": "GET",
                    "parse_json": True
                },
                "ResultExpr": "$.json.url",
                "OutputExpr": "$",
                "End": True
            }
        }
    })

    engine = WorkflowEngine(hook=PrintHook())
    result = await engine.run("http-run-001", dsl, {})
    assert "httpbin.org" in result
