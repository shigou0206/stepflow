#!/usr/bin/env python
# scripts/test_activity_types.py

import requests
import json
import uuid
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

# 测试不同的活动类型名称
activity_types = [
    "HttpTool",
    "ShellTool",
]

for activity_type in activity_types:
    logger.info(f"\n=== 测试活动类型: {activity_type} ===")
    
    # 创建简单工作流模板
    template_id = f"test-{uuid.uuid4()}"
    
    # 根据活动类型设置不同的参数
    parameters = {}
    if "http" in activity_type.lower():
        parameters = {
            "url": "https://httpbin.org/get",
            "method": "GET",
            "timeout": 5
        }
        logger.info(f"HTTP 工具参数: {parameters}")
    elif "shell" in activity_type.lower():
        parameters = {
            "command": "echo 'Hello from ShellTool'",
            "timeout": 5,
            "shell": True
        }
        logger.info(f"Shell 工具参数: {parameters}")
    
    workflow_dsl = {
        "Version": "1.0",
        "Name": "TestWorkflow",
        "StartAt": "TestActivity",
        "States": {
            "TestActivity": {
                "Type": "Task",
                "ActivityType": activity_type,
                "Parameters": parameters,
                "End": True
            }
        }
    }
    
    logger.info(f"工作流定义: {json.dumps(workflow_dsl, indent=2)}")
    
    template_data = {
        "name": f"测试{activity_type}",
        "description": f"测试{activity_type}活动类型",
        "template_id": template_id,
        "dsl_definition": json.dumps(workflow_dsl)
    }
    
    # 创建模板
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        logger.error(f"创建工作流模板失败: {response.text}")
        continue
    
    logger.info(f"创建模板成功: {template_id}")
    
    # 启动工作流
    workflow_data = {
        "template_id": template_id,
        "input": {
            "timestamp": datetime.now().isoformat()
        }
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=workflow_data)
    if response.status_code != 200:
        logger.error(f"启动工作流失败: {response.text}")
        continue
    
    result = response.json()
    run_id = result.get("run_id")
    logger.info(f"启动工作流成功，run_id: {run_id}")
    
    # 等待工作流完成
    import time
    for i in range(10):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
        if response.status_code == 200:
            status = response.json().get("status")
            logger.info(f"轮询 {i+1}/10: 状态: {status}")
            if status in ["completed", "failed", "canceled"]:
                break
    
    # 检查结果
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    if response.status_code == 200:
        result = response.json()
        logger.info(f"最终结果: {result.get('status')}")
        
        # 获取活动任务结果
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}/tasks")
        if response.status_code == 200:
            tasks = response.json()
            logger.info(f"活动任务: {json.dumps(tasks, indent=2)}") 