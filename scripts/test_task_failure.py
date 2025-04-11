#!/usr/bin/env python
# scripts/test_task_failure.py

import requests
import json
import uuid
from datetime import datetime
import logging
import time

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

def test_http_failure():
    """测试 HTTP 工具失败处理"""
    logger.info("=== 测试 HTTP 工具失败处理 ===")
    
    # 创建工作流模板 - 使用无效的 URL
    template_id = f"test-http-fail-{uuid.uuid4()}"
    workflow_dsl = {
        "Version": "1.0",
        "Name": "TestHttpFailure",
        "StartAt": "FailingHttpTask",
        "States": {
            "FailingHttpTask": {
                "Type": "Task",
                "ActivityType": "HttpTool",
                "Parameters": {
                    "url": "https://nonexistent-domain-12345.com",
                    "method": "GET",
                    "timeout": 5
                },
                "End": True
            }
        }
    }
    
    template_data = {
        "name": "测试HTTP失败",
        "description": "测试HTTP工具失败处理",
        "template_id": template_id,
        "dsl_definition": json.dumps(workflow_dsl)
    }
    
    # 创建模板
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        logger.error(f"创建工作流模板失败: {response.text}")
        return
    
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
        return
    
    result = response.json()
    run_id = result.get("run_id")
    logger.info(f"启动工作流成功，run_id: {run_id}")
    
    # 等待工作流完成
    for i in range(20):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
        if response.status_code == 200:
            status = response.json().get("status")
            logger.info(f"轮询 {i+1}/20: 状态: {status}")
            if status in ["completed", "failed", "canceled"]:
                break
    
    # 检查最终状态
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    if response.status_code == 200:
        result = response.json()
        logger.info(f"最终状态: {result.get('status')}")
        logger.info(f"结果: {result.get('result')}")
        
        # 获取活动任务
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}/tasks")
        if response.status_code == 200:
            tasks = response.json()
            for task in tasks:
                logger.info(f"任务 {task.get('task_token')}: 状态={task.get('status')}")
                if task.get("error"):
                    logger.info(f"错误: {task.get('error')}")
                    logger.info(f"错误详情: {task.get('error_details')}")

def test_shell_failure():
    """测试 Shell 工具失败处理"""
    logger.info("\n=== 测试 Shell 工具失败处理 ===")
    
    # 创建工作流模板 - 使用无效的命令
    template_id = f"test-shell-fail-{uuid.uuid4()}"
    workflow_dsl = {
        "Version": "1.0",
        "Name": "TestShellFailure",
        "StartAt": "FailingShellTask",
        "States": {
            "FailingShellTask": {
                "Type": "Task",
                "ActivityType": "ShellTool",
                "Parameters": {
                    "command": "nonexistent_command_12345",
                    "timeout": 5,
                    "shell": True
                },
                "End": True
            }
        }
    }
    
    template_data = {
        "name": "测试Shell失败",
        "description": "测试Shell工具失败处理",
        "template_id": template_id,
        "dsl_definition": json.dumps(workflow_dsl)
    }
    
    # 创建模板
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        logger.error(f"创建工作流模板失败: {response.text}")
        return
    
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
        return
    
    result = response.json()
    run_id = result.get("run_id")
    logger.info(f"启动工作流成功，run_id: {run_id}")
    
    # 等待工作流完成
    for i in range(20):
        time.sleep(1)
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
        if response.status_code == 200:
            status = response.json().get("status")
            logger.info(f"轮询 {i+1}/20: 状态: {status}")
            if status in ["completed", "failed", "canceled"]:
                break
    
    # 检查最终状态
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    if response.status_code == 200:
        result = response.json()
        logger.info(f"最终状态: {result.get('status')}")
        logger.info(f"结果: {result.get('result')}")
        
        # 获取活动任务
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}/tasks")
        if response.status_code == 200:
            tasks = response.json()
            for task in tasks:
                logger.info(f"任务 {task.get('task_token')}: 状态={task.get('status')}")
                if task.get("error"):
                    logger.info(f"错误: {task.get('error')}")
                    logger.info(f"错误详情: {task.get('error_details')}")

if __name__ == "__main__":
    test_http_failure()
    test_shell_failure() 