#!/usr/bin/env python
# scripts/test_single_tool.py

import requests
import json
import uuid
import sys
from datetime import datetime

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

def test_tool(tool_name, parameters):
    """测试单个工具"""
    print(f"=== 测试工具: {tool_name} ===")
    
    # 创建简单工作流模板
    template_id = f"test-{tool_name.lower()}-{uuid.uuid4()}"
    workflow_dsl = {
        "Version": "1.0",
        "Name": f"Test{tool_name}Workflow",
        "StartAt": "TestActivity",
        "States": {
            "TestActivity": {
                "Type": "Task",
                "ActivityType": tool_name,
                "Parameters": parameters,
                "End": True
            }
        }
    }
    
    template_data = {
        "name": f"测试{tool_name}工具",
        "description": f"用于测试{tool_name}工具的简单工作流",
        "template_id": template_id,
        "dsl_definition": json.dumps(workflow_dsl)
    }
    
    # 创建模板
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        print(f"创建工作流模板失败: {response.text}")
        return
    
    print(f"创建工作流模板成功: {template_id}")
    
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
        return
    
    result = response.json()
    run_id = result.get("run_id")
    print(f"启动工作流成功，run_id: {run_id}")
    
    # 等待工作流完成
    print("等待工作流执行...")
    import time
    for _ in range(30):  # 最多等待30秒
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
        if response.status_code == 200:
            status = response.json().get("status")
            print(f"当前状态: {status}")
            if status in ["completed", "failed", "canceled"]:
                break
    
    # 检查结果
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    if response.status_code == 200:
        result = response.json()
        print(f"工作流执行结果:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"获取工作流结果失败: {response.text}")
        return None

if __name__ == "__main__":
    # 测试 ShellTool
    test_tool("ShellTool", {
        "command": "echo 'Hello, World!'",
        "timeout": 5
    })
    
    print("\n" + "="*50 + "\n")
    
    # 测试 HttpTool
    test_tool("HttpTool", {
        "url": "https://httpbin.org/get",
        "method": "GET",
        "timeout": 5
    }) 