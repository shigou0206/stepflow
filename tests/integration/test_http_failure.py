import pytest
import json
import time
from fastapi.testclient import TestClient

from stepflow.main import app

client = TestClient(app)

def test_http_task_failure_handling():
    """测试 HTTP 任务失败时工作流状态正确更新为 failed"""
    
    # 1. 创建一个包含无效 URL 的 HTTP 工作流模板
    template_data = {
        "name": "HTTP失败测试工作流",
        "description": "测试 HTTP 任务失败时的工作流状态",
        "template_id": "http-failure-test",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "HTTPFailureWorkflow",
            "StartAt": "FailingHTTPCall",
            "States": {
                "FailingHTTPCall": {
                    "Type": "Task",
                    "ActivityType": "HTTPTool",
                    "Parameters": {
                        "url": "https://non-existent-domain-12345.example",
                        "method": "GET",
                        "timeout": 2
                    },
                    "End": True
                }
            }
        })
    }
    
    response = client.post("/workflow_templates/", json=template_data)
    assert response.status_code == 200
    
    # 2. 执行工作流
    execution_data = {
        "workflow_id": "http-failure-test-execution",
        "template_id": "http-failure-test",
        "input": {}
    }
    
    response = client.post("/workflow_executions/", json=execution_data)
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    
    # 3. 等待足够时间让工作流执行完成
    time.sleep(5)
    
    # 4. 检查工作流状态是否为 failed
    response = client.get(f"/workflow_executions/{run_id}")
    assert response.status_code == 200
    execution = response.json()
    
    print(f"工作流执行状态: {execution['status']}")
    print(f"工作流执行结果: {execution['result']}")
    
    assert execution["status"] == "failed", "工作流状态应该是 failed，但实际是 " + execution["status"]
    
    # 5. 检查工作流事件
    response = client.get(f"/workflow_events/{run_id}")
    assert response.status_code == 200
    events = response.json()
    
    # 应该有一个 ACTIVITY_TASK_FAILED 事件
    failed_events = [e for e in events if e["event_type"] == "ACTIVITY_TASK_FAILED"]
    assert len(failed_events) > 0, "应该有 ACTIVITY_TASK_FAILED 事件"
    
    print("测试通过: HTTP 任务失败时工作流状态正确更新为 failed") 