#!/usr/bin/env python
# scripts/test_parallel_workflows.py

import asyncio
import json
import time
import uuid
import requests
from concurrent.futures import ThreadPoolExecutor

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

# 要并行执行的工作流数量
NUM_WORKFLOWS = 10

def create_workflow_template():
    """创建一个测试工作流模板"""
    template_id = f"parallel-test-template-{uuid.uuid4()}"
    template_data = {
        "name": "并行测试工作流",
        "description": "用于测试并行执行的工作流",
        "template_id": template_id,
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "ParallelTestWorkflow",
            "StartAt": "HTTPCall",
            "States": {
                "HTTPCall": {
                    "Type": "Task",
                    "ActivityType": "HTTPTool",
                    "Parameters": {
                        "url": "https://jsonplaceholder.typicode.com/todos/1",
                        "method": "GET",
                        "timeout": 5
                    },
                    "Next": "Wait"
                },
                "Wait": {
                    "Type": "Wait",
                    "Seconds": 2,
                    "Next": "FinalState"
                },
                "FinalState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        raise Exception(f"创建工作流模板失败: {response.text}")
    
    return template_id

def start_workflow(template_id, index):
    """启动一个工作流执行"""
    workflow_id = f"parallel-test-{index}-{uuid.uuid4()}"
    execution_data = {
        "workflow_id": workflow_id,
        "template_id": template_id,
        "input": {
            "index": index,
            "timestamp": time.time()
        }
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    if response.status_code != 200:
        raise Exception(f"启动工作流执行失败: {response.text}")
    
    run_id = response.json()["run_id"]
    print(f"工作流 {index} 启动成功，run_id: {run_id}")
    return run_id

def check_workflow_status(run_id, index):
    """检查工作流执行状态"""
    max_retries = 30
    for i in range(max_retries):
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
        if response.status_code != 200:
            print(f"获取工作流 {index} 状态失败: {response.text}")
            return False
        
        execution = response.json()
        status = execution["status"]
        
        if status == "completed":
            print(f"工作流 {index} 执行完成")
            return True
        elif status == "failed":
            print(f"工作流 {index} 执行失败: {execution.get('result', '')}")
            return False
        
        # 等待一段时间后再次检查
        time.sleep(1)
    
    print(f"工作流 {index} 执行超时")
    return False

def main():
    """主函数"""
    print(f"===== 测试并行执行 {NUM_WORKFLOWS} 个工作流 =====")
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("服务未正常运行，请先启动服务")
            return
    except requests.exceptions.ConnectionError:
        print("无法连接到服务，请先启动服务")
        return
    
    # 创建工作流模板
    try:
        template_id = create_workflow_template()
        print(f"创建工作流模板成功，template_id: {template_id}")
    except Exception as e:
        print(f"创建工作流模板失败: {str(e)}")
        return
    
    # 并行启动多个工作流
    run_ids = []
    with ThreadPoolExecutor(max_workers=NUM_WORKFLOWS) as executor:
        futures = [executor.submit(start_workflow, template_id, i) for i in range(NUM_WORKFLOWS)]
        for future in futures:
            try:
                run_id = future.result()
                run_ids.append(run_id)
            except Exception as e:
                print(f"启动工作流失败: {str(e)}")
    
    print(f"已启动 {len(run_ids)} 个工作流")
    
    # 检查所有工作流的执行状态
    success_count = 0
    with ThreadPoolExecutor(max_workers=NUM_WORKFLOWS) as executor:
        futures = [executor.submit(check_workflow_status, run_id, i) for i, run_id in enumerate(run_ids)]
        for future in futures:
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                print(f"检查工作流状态失败: {str(e)}")
    
    print(f"\n===== 测试结果 =====")
    print(f"总工作流数: {NUM_WORKFLOWS}")
    print(f"成功完成: {success_count}")
    print(f"失败或超时: {NUM_WORKFLOWS - success_count}")
    
    if success_count == NUM_WORKFLOWS:
        print("测试通过: 所有工作流都成功并行执行")
    else:
        print("测试失败: 部分工作流执行失败或超时")

if __name__ == "__main__":
    main() 