import pytest
import json
import time
import uuid
from fastapi.testclient import TestClient

from stepflow.main import app

client = TestClient(app)

def test_http_task_failure_handling():
    """测试 HTTP 任务失败时工作流状态正确更新为 failed"""
    
    # 使用唯一的模板 ID
    unique_id = str(uuid.uuid4())
    template_id = f"http-failure-test-{unique_id}"
    
    print(f"使用唯一模板 ID: {template_id}")
    
    # 1. 创建一个包含无效 URL 的 HTTP 工作流模板
    template_data = {
        "name": f"HTTP失败测试工作流-{unique_id}",
        "description": "测试 HTTP 任务失败时的工作流状态",
        "template_id": template_id,
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "HTTPFailureWorkflow",
            "StartAt": "FailingHTTPCall",
            "States": {
                "FailingHTTPCall": {
                    "Type": "Task",
                    "ActivityType": "HttpTool",
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
    assert response.status_code == 200, f"创建模板失败: {response.text}"
    
    # 2. 执行工作流
    execution_data = {
        "template_id": template_id,
        "input": {}
    }
    
    response = client.post("/workflow_executions/", json=execution_data)
    assert response.status_code == 200, f"启动工作流失败: {response.text}"
    run_id = response.json()["run_id"]
    
    print(f"工作流启动成功，run_id: {run_id}")
    
    # 3. 等待足够时间让工作流执行完成 - 增加等待时间
    max_wait = 30  # 最多等待30秒
    execution = None
    
    for i in range(max_wait):
        response = client.get(f"/workflow_executions/{run_id}")
        assert response.status_code == 200, f"获取工作流状态失败: {response.text}"
        execution = response.json()
        print(f"轮询 {i+1}/{max_wait}: 工作流状态 = {execution.get('status')}")
        
        if execution.get('status') in ['completed', 'failed', 'canceled']:
            break
        time.sleep(1)
    
    assert execution is not None, "未能获取工作流执行信息"
    
    # 4. 检查工作流状态是否为 failed
    assert execution.get('status') == 'failed', f"工作流状态应为 'failed'，实际为 '{execution.get('status')}'"
    
    # 检查结果字段，可能不存在
    result = execution.get('result')
    print(f"工作流执行结果: {result}")
    
    # 确保结果包含错误信息
    if result:
        result_data = json.loads(result) if isinstance(result, str) else result
        assert "error" in result_data, "工作流结果应包含错误信息"
        print(f"错误信息: {result_data.get('error')}")
    
    # 5. 检查活动任务状态
    response = client.get(f"/workflow_executions/{run_id}/tasks")
    assert response.status_code == 200, f"获取活动任务失败: {response.text}"
    tasks = response.json()
    
    # 应该至少有一个任务
    assert len(tasks) > 0, "没有找到活动任务"
    
    # 检查任务状态
    task = tasks[0]
    print(f"活动任务状态: {task.get('status')}")
    print(f"活动任务完整信息: {json.dumps(task, indent=2)}")
    
    # 检查任务错误信息
    assert task.get('status') == 'failed', f"任务状态应为 'failed'，实际为 '{task.get('status')}'"
    
    # 如果错误字段不存在，尝试直接查询数据库
    if task.get('error') is None:
        print("警告: API 响应中缺少错误信息，尝试直接查询数据库...")
        
        # 使用 requests 直接查询数据库 API
        response = client.get(f"/activity_tasks/{task.get('task_token')}")
        if response.status_code == 200:
            db_task = response.json()
            print(f"数据库中的任务信息: {json.dumps(db_task, indent=2)}")
            
            # 使用数据库中的错误信息
            if db_task.get('error'):
                print(f"数据库中的错误信息: {db_task.get('error')}")
                assert db_task.get('error') is not None, "数据库中的任务也没有错误信息"
            else:
                assert False, "数据库中的任务也没有错误信息"
    else:
        assert task.get('error') is not None, "任务应包含错误信息"
        print(f"任务错误信息: {task.get('error')}")
    
    print("测试通过: HTTP 任务失败时工作流状态正确更新为 failed") 