#!/usr/bin/env python
# scripts/test_activity_types.py

import requests
import json
import uuid
from datetime import datetime

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

# 测试不同的活动类型名称
activity_types = [
    "HttpTool",
    "ShellTool",
]

for activity_type in activity_types:
    print(f"\n=== 测试活动类型: {activity_type} ===")
    
    # 创建简单工作流模板
    template_id = f"test-{uuid.uuid4()}"
    workflow_dsl = {
        "Version": "1.0",
        "Name": "TestWorkflow",
        "StartAt": "TestActivity",
        "States": {
            "TestActivity": {
                "Type": "Task",
                "ActivityType": activity_type,
                "Parameters": {
                    "url": "https://httpbin.org/get" if "http" in activity_type.lower() else None,
                    "command": "echo 'Hello'" if "shell" in activity_type.lower() else None,
                    "timeout": 5
                },
                "End": True
            }
        }
    }
    
    template_data = {
        "name": f"测试{activity_type}",
        "description": f"测试{activity_type}活动类型",
        "template_id": template_id,
        "dsl_definition": json.dumps(workflow_dsl)
    }
    
    # 创建模板
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        print(f"创建工作流模板失败: {response.text}")
        continue
    
    # 启动工作流
    workflow_data = {
        "template_id": template_id,
        "input": {
            "timestamp": datetime.now().isoformat()
        }
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=workflow_data)
    if response.status_code != 200:
        print(f"启动工作流失败: {response.text}")
        continue
    
    result = response.json()
    run_id = result.get("run_id")
    print(f"启动工作流成功，run_id: {run_id}")
    
    # 等待工作流完成
    import time
    for _ in range(10):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
        if response.status_code == 200:
            status = response.json().get("status")
            print(f"状态: {status}")
            if status in ["completed", "failed", "canceled"]:
                break
    
    # 检查结果
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    if response.status_code == 200:
        result = response.json()
        print(f"结果: {result.get('status')}") 