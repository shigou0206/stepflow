import pytest
from typing import Optional
from stepflow.dsl.dsl_model import WorkflowDSL
from stepflow.hooks.base import ExecutionHooks
from stepflow.worker.tools.tool_registry import tool_registry
from stepflow.worker.tools.http_tool import HttpTool
from stepflow.engine.workflow_engine import WorkflowEngine
from stepflow.tests.mocks.execution_service import MockExecutionService
from stepflow.hooks.print_hook import PrintHook


@pytest.mark.asyncio
async def test_http_tool_task():
    tool_registry["HttpTool"] = HttpTool()

    dsl = WorkflowDSL.model_validate({
        "StartAt": "FetchData",
        "States": {
            "FetchData": {
                "Type": "Task",
                "Resource": "HttpTool",
                "Parameters": {
                    "url": "http://httpbin.org/get",
                    "method": "GET",
                    "parse_json": True
                },
                "ResultExpr": "$.json.url",
                "OutputExpr": "$",
                "End": True
            }
        }
    })

    engine = WorkflowEngine(hook=PrintHook(), execution_service=MockExecutionService())  # 如果 run() 中未访问 execution_service，可设为 None
    result = await engine.run("test-http-tool", dsl, {})
    
    assert isinstance(result, str)
    assert "httpbin.org" in result