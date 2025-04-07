#!/usr/bin/env python
# scripts/test_api_endpoints.py

import requests
import json
import time
import sys

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

def test_workflow_template_endpoints():
    """测试工作流模板端点"""
    print("\n测试工作流模板端点...")
    
    # 创建模板
    template_data = {
        "name": "Test Template",
        "description": "A test workflow template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "TestWorkflow",
            "StartAt": "PassState",
            "States": {
                "PassState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    print(f"创建模板响应: {response.status_code}")
    if response.status_code == 200:
        template_id = response.json()["template_id"]
        print(f"创建的模板 ID: {template_id}")
        
        # 获取模板
        response = requests.get(f"{BASE_URL}/workflow_templates/{template_id}")
        print(f"获取模板响应: {response.status_code}")
        if response.status_code == 200:
            print(f"模板内容: {response.json()}")
        
        # 列出所有模板
        response = requests.get(f"{BASE_URL}/workflow_templates/")
        print(f"列出模板响应: {response.status_code}")
        if response.status_code == 200:
            templates = response.json()
            print(f"模板数量: {len(templates)}")
        
        # 删除模板
        response = requests.delete(f"{BASE_URL}/workflow_templates/{template_id}")
        print(f"删除模板响应: {response.status_code}")
        
        # 验证删除
        response = requests.get(f"{BASE_URL}/workflow_templates/{template_id}")
        print(f"验证删除响应: {response.status_code}")
    
    return True

def test_workflow_visibility_endpoint():
    """测试工作流可见性端点"""
    print("\n测试工作流可见性端点...")
    
    # 创建模板
    template_data = {
        "name": "Visibility Test Template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "VisibilityTestWorkflow",
            "StartAt": "PassState",
            "States": {
                "PassState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code == 200:
        template_id = response.json()["template_id"]
        
        # 启动工作流执行
        execution_data = {
            "workflow_id": "visibility-test-execution",
            "template_id": template_id,
            "input": {"test": "data"}
        }
        
        response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
        print(f"启动工作流响应: {response.status_code}")
        if response.status_code == 200:
            run_id = response.json()["run_id"]
            print(f"工作流执行 ID: {run_id}")
            
            # 等待工作流完成
            time.sleep(2)
            
            # 获取工作流可见性
            response = requests.get(f"{BASE_URL}/workflow_visibility/{run_id}")
            print(f"获取工作流可见性响应: {response.status_code}")
            if response.status_code == 200:
                visibility = response.json()
                print(f"工作流可见性: {visibility}")
            else:
                print(f"获取工作流可见性失败: {response.text}")
    
    return True

def test_activity_task_failure():
    """测试活动任务失败处理"""
    print("\n测试活动任务失败处理...")
    
    # 创建模板
    template_data = {
        "name": "Failure Test Template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "FailureTestWorkflow",
            "StartAt": "TaskState",
            "States": {
                "TaskState": {
                    "Type": "Task",
                    "ActivityType": "SimpleTask",
                    "End": True
                }
            }
        })
    }
    
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code == 200:
        template_id = response.json()["template_id"]
        
        # 启动工作流执行
        execution_data = {
            "workflow_id": "failure-test-execution",
            "template_id": template_id,
            "input": {"test": "data"}
        }
        
        response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
        print(f"启动工作流响应: {response.status_code}")
        if response.status_code == 200:
            run_id = response.json()["run_id"]
            print(f"工作流执行 ID: {run_id}")
            
            # 等待活动任务创建
            time.sleep(1)
            
            # 获取活动任务
            response = requests.get(f"{BASE_URL}/activity_tasks/run/{run_id}")
            print(f"获取活动任务响应: {response.status_code}")
            if response.status_code == 200:
                tasks = response.json()
                if tasks:
                    task = tasks[0]
                    task_token = task["task_token"]
                    print(f"活动任务 Token: {task_token}")
                    
                    # 启动活动任务
                    response = requests.post(f"{BASE_URL}/activity_tasks/{task_token}/start")
                    print(f"启动活动任务响应: {response.status_code}")
                    
                    # 使任务失败
                    fail_data = {
                        "reason": "Test failure",
                        "details": json.dumps({"error": "Test error"})
                    }
                    response = requests.post(f"{BASE_URL}/activity_tasks/{task_token}/fail", json=fail_data)
                    print(f"使任务失败响应: {response.status_code}")
                    
                    # 等待工作流状态更新
                    time.sleep(2)
                    
                    # 获取工作流执行状态
                    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
                    print(f"获取工作流状态响应: {response.status_code}")
                    if response.status_code == 200:
                        execution = response.json()
                        print(f"工作流状态: {execution['status']}")
                        if execution["status"] == "failed":
                            print("测试成功: 工作流状态已更新为失败")
                        else:
                            print(f"测试失败: 工作流状态为 {execution['status']}，而不是 failed")
                    else:
                        print(f"获取工作流状态失败: {response.text}")
                else:
                    print("没有找到活动任务")
            else:
                print(f"获取活动任务失败: {response.text}")
    
    return True

def main():
    """主函数"""
    print("测试 API 端点...")
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"服务状态: {response.status_code}")
        if response.status_code != 200:
            print("服务未正常运行，请先启动服务")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("无法连接到服务，请先启动服务")
        sys.exit(1)
    
    # 运行测试
    tests = [
        test_workflow_template_endpoints,
        test_workflow_visibility_endpoint,
        test_activity_task_failure
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"测试失败: {e}")
    
    print("\n测试完成")

if __name__ == "__main__":
    main() 