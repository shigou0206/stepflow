#!/usr/bin/env python
# scripts/test_api_examples.py

import requests
import json
import time
import uuid
from datetime import datetime, timedelta

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

def print_response(response, message=""):
    """打印响应内容"""
    print(f"\n{message}")
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应内容: {response.text}")

def test_health_check():
    """测试 API 健康检查"""
    print("\n===== 测试 API 健康检查 =====")
    response = requests.get(f"{BASE_URL}/")
    print_response(response, "API 健康检查响应:")
    return response.status_code == 200

def test_workflow_templates():
    """测试工作流模板 API"""
    print("\n===== 测试工作流模板 API =====")
    
    # 1. 创建工作流模板
    template_id = f"test-template-{uuid.uuid4()}"
    template_data = {
        "name": "测试工作流模板",
        "description": "这是一个用于测试的工作流模板",
        "template_id": template_id,
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
    
    print(f"\n创建工作流模板请求数据:\n{json.dumps(template_data, indent=2, ensure_ascii=False)}")
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    print_response(response, "创建工作流模板响应:")
    
    if response.status_code != 200:
        print("创建工作流模板失败，跳过后续测试")
        return False
    
    # 2. 获取工作流模板
    response = requests.get(f"{BASE_URL}/workflow_templates/{template_id}")
    print_response(response, "获取工作流模板响应:")
    
    # 3. 列出所有工作流模板
    response = requests.get(f"{BASE_URL}/workflow_templates/")
    print_response(response, "列出所有工作流模板响应:")
    
    # 4. 更新工作流模板
    update_data = {
        "name": "更新后的测试工作流模板",
        "description": "这是一个更新后的工作流模板描述"
    }
    response = requests.put(f"{BASE_URL}/workflow_templates/{template_id}", json=update_data)
    print_response(response, "更新工作流模板响应:")
    
    # 5. 删除工作流模板
    response = requests.delete(f"{BASE_URL}/workflow_templates/{template_id}")
    print_response(response, "删除工作流模板响应:")
    
    return True

def test_workflow_executions():
    """测试工作流执行 API"""
    print("\n===== 测试工作流执行 API =====")
    
    # 1. 创建工作流模板
    template_id = f"test-execution-template-{uuid.uuid4()}"
    template_data = {
        "name": "执行测试模板",
        "description": "用于测试工作流执行的模板",
        "template_id": template_id,
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "ExecutionTestWorkflow",
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
    if response.status_code != 200:
        print("创建工作流模板失败，跳过工作流执行测试")
        return False
    
    # 2. 启动工作流执行
    workflow_id = f"test-execution-{uuid.uuid4()}"
    execution_data = {
        "workflow_id": workflow_id,
        "template_id": template_id,
        "input": {"test_key": "test_value"},
        "workflow_type": "TestExecution",
        "memo": "这是一个测试执行",
        "search_attrs": {"attr1": "value1", "attr2": "value2"}
    }
    
    print(f"\n启动工作流执行请求数据:\n{json.dumps(execution_data, indent=2, ensure_ascii=False)}")
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    print_response(response, "启动工作流执行响应:")
    
    if response.status_code != 200:
        print("启动工作流执行失败，跳过后续测试")
        return False
    
    run_id = response.json()["run_id"]
    
    # 3. 获取工作流执行状态
    time.sleep(1)  # 等待工作流启动
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    print_response(response, "获取工作流执行状态响应:")
    
    # 4. 列出所有工作流执行
    response = requests.get(f"{BASE_URL}/workflow_executions/")
    print_response(response, "列出所有工作流执行响应:")
    
    # 5. 按状态列出工作流执行
    response = requests.get(f"{BASE_URL}/workflow_executions/?status=running")
    print_response(response, "按状态列出工作流执行响应:")
    
    return True

def test_activity_tasks():
    """测试活动任务 API"""
    print("\n===== 测试活动任务 API =====")
    
    # 1. 创建工作流模板
    template_id = f"test-activity-template-{uuid.uuid4()}"
    template_data = {
        "name": "活动任务测试模板",
        "description": "用于测试活动任务的模板",
        "template_id": template_id,
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "ActivityTestWorkflow",
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
    if response.status_code != 200:
        print("创建工作流模板失败，跳过活动任务测试")
        return False
    
    # 2. 启动工作流执行
    workflow_id = f"test-activity-{uuid.uuid4()}"
    execution_data = {
        "workflow_id": workflow_id,
        "template_id": template_id,
        "input": {"test_key": "test_value"}
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    if response.status_code != 200:
        print("启动工作流执行失败，跳过后续测试")
        return False
    
    run_id = response.json()["run_id"]
    
    # 3. 获取活动任务
    time.sleep(1)  # 等待任务创建
    response = requests.get(f"{BASE_URL}/activity_tasks/run/{run_id}")
    print_response(response, "获取活动任务响应:")
    
    if response.status_code != 200 or len(response.json()) == 0:
        print("没有找到活动任务，跳过后续测试")
        return False
    
    task_token = response.json()[0]["task_token"]
    
    # 4. 启动活动任务
    response = requests.post(f"{BASE_URL}/activity_tasks/{task_token}/start")
    print_response(response, "启动活动任务响应:")
    
    # 5. 发送活动任务心跳
    heartbeat_data = {
        "details": "任务正在进行中..."
    }
    response = requests.post(f"{BASE_URL}/activity_tasks/{task_token}/heartbeat", json=heartbeat_data)
    print_response(response, "发送活动任务心跳响应:")
    
    # 6. 完成活动任务
    complete_data = {
        "result_data": json.dumps({"result": "success", "data": "任务完成"})
    }
    response = requests.post(f"{BASE_URL}/activity_tasks/{task_token}/complete", json=complete_data)
    print_response(response, "完成活动任务响应:")
    
    # 7. 验证工作流状态
    time.sleep(1)
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    print_response(response, "验证工作流状态响应:")
    
    return True

def test_workflow_visibility():
    """测试工作流可见性 API"""
    print("\n===== 测试工作流可见性 API =====")
    
    # 1. 创建并执行一个工作流
    template_id = f"test-visibility-template-{uuid.uuid4()}"
    template_data = {
        "name": "可见性测试模板",
        "template_id": template_id,
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
    if response.status_code != 200:
        print("创建工作流模板失败，跳过可见性测试")
        return False
    
    workflow_id = f"test-visibility-{uuid.uuid4()}"
    execution_data = {
        "workflow_id": workflow_id,
        "template_id": template_id,
        "input": {"test_key": "test_value"}
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    if response.status_code != 200:
        print("启动工作流执行失败，跳过后续测试")
        return False
    
    run_id = response.json()["run_id"]
    
    # 2. 获取工作流可见性
    time.sleep(1)
    response = requests.get(f"{BASE_URL}/workflow_visibility/{run_id}")
    print_response(response, "获取工作流可见性响应:")
    
    # 3. 列出所有工作流可见性
    response = requests.get(f"{BASE_URL}/workflow_visibility/")
    print_response(response, "列出所有工作流可见性响应:")
    
    # 4. 按状态列出工作流可见性
    response = requests.get(f"{BASE_URL}/workflow_visibility/?status=completed")
    print_response(response, "按状态列出工作流可见性响应:")
    
    return True

def test_workflow_events():
    """测试工作流事件 API"""
    print("\n===== 测试工作流事件 API =====")
    
    # 1. 创建并执行一个工作流
    template_id = f"test-events-template-{uuid.uuid4()}"
    template_data = {
        "name": "事件测试模板",
        "template_id": template_id,
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "EventsTestWorkflow",
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
    if response.status_code != 200:
        print("创建工作流模板失败，跳过事件测试")
        return False
    
    workflow_id = f"test-events-{uuid.uuid4()}"
    execution_data = {
        "workflow_id": workflow_id,
        "template_id": template_id,
        "input": {"test_key": "test_value"}
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    if response.status_code != 200:
        print("启动工作流执行失败，跳过后续测试")
        return False
    
    run_id = response.json()["run_id"]
    
    # 2. 获取工作流事件
    time.sleep(1)
    response = requests.get(f"{BASE_URL}/workflow_events/{run_id}")
    print_response(response, "获取工作流事件响应:")
    
    return True

def test_timers():
    """测试定时器 API"""
    print("\n===== 测试定时器 API =====")
    
    # 1. 创建并执行一个工作流
    template_id = f"test-timer-template-{uuid.uuid4()}"
    template_data = {
        "name": "定时器测试模板",
        "template_id": template_id,
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "TimerTestWorkflow",
            "StartAt": "WaitState",
            "States": {
                "WaitState": {
                    "Type": "Wait",
                    "Seconds": 5,
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
        print("创建工作流模板失败，跳过定时器测试")
        return False
    
    workflow_id = f"test-timer-{uuid.uuid4()}"
    execution_data = {
        "workflow_id": workflow_id,
        "template_id": template_id,
        "input": {"test_key": "test_value"}
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    if response.status_code != 200:
        print("启动工作流执行失败，跳过后续测试")
        return False
    
    run_id = response.json()["run_id"]
    
    # 2. 获取定时器
    time.sleep(1)
    response = requests.get(f"{BASE_URL}/timers/run/{run_id}")
    print_response(response, "获取定时器响应:")
    
    # 3. 等待定时器触发
    print("\n等待定时器触发...")
    time.sleep(6)
    
    # 4. 验证工作流状态
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    print_response(response, "验证工作流状态响应:")
    
    return True

def main():
    """主函数"""
    print("===== StepFlow API 测试样例 =====")
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("服务未正常运行，请先启动服务")
            return
    except requests.exceptions.ConnectionError:
        print("无法连接到服务，请先启动服务")
        return
    
    # 运行测试
    tests = [
        test_health_check,
        test_workflow_templates,
        test_workflow_executions,
        test_activity_tasks,
        test_workflow_visibility,
        test_workflow_events,
        test_timers
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"测试失败: {e}")
    
    print("\n===== 测试完成 =====")

if __name__ == "__main__":
    main() 