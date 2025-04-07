#!/usr/bin/env python
# scripts/test_http_failure.py

import requests
import json
import time
import sys

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

def test_http_failure():
    """测试 HTTP 任务失败时工作流状态正确更新为 failed"""
    print("\n===== 测试 HTTP 任务失败处理 =====")
    
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
    
    print(f"\n创建工作流模板请求数据:\n{json.dumps(template_data, indent=2, ensure_ascii=False)}")
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    print_response(response, "创建工作流模板响应:")
    
    if response.status_code != 200:
        print("创建工作流模板失败，跳过后续测试")
        return False
    
    # 2. 执行工作流
    execution_data = {
        "workflow_id": "http-failure-test-execution",
        "template_id": "http-failure-test",
        "input": {}
    }
    
    print(f"\n启动工作流执行请求数据:\n{json.dumps(execution_data, indent=2, ensure_ascii=False)}")
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    print_response(response, "启动工作流执行响应:")
    
    if response.status_code != 200:
        print("启动工作流执行失败，跳过后续测试")
        return False
    
    run_id = response.json()["run_id"]
    
    # 3. 等待足够时间让工作流执行完成
    print("\n等待工作流执行完成...")
    for i in range(10):
        time.sleep(1)
        print(".", end="", flush=True)
    print("\n")
    
    # 4. 检查工作流状态是否为 failed
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    print_response(response, "工作流执行状态响应:")
    
    if response.status_code != 200:
        print("获取工作流执行状态失败")
        return False
    
    execution = response.json()
    print(f"工作流执行状态: {execution['status']}")
    
    if execution["status"] == "failed":
        print("测试通过: HTTP 任务失败时工作流状态正确更新为 failed")
    else:
        print(f"测试失败: 工作流状态应该是 failed，但实际是 {execution['status']}")
        return False
    
    # 5. 检查工作流事件
    response = requests.get(f"{BASE_URL}/workflow_events/{run_id}")
    print_response(response, "工作流事件响应:")
    
    if response.status_code != 200:
        print("获取工作流事件失败")
        return False
    
    events = response.json()
    failed_events = [e for e in events if e["event_type"] == "ACTIVITY_TASK_FAILED"]
    
    if len(failed_events) > 0:
        print("测试通过: 存在 ACTIVITY_TASK_FAILED 事件")
    else:
        print("测试失败: 应该有 ACTIVITY_TASK_FAILED 事件")
        return False
    
    return True

def main():
    """主函数"""
    print("===== HTTP 工具失败处理测试 =====")
    
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
    success = test_http_failure()
    
    if success:
        print("\n===== 测试成功 =====")
        sys.exit(0)
    else:
        print("\n===== 测试失败 =====")
        sys.exit(1)

if __name__ == "__main__":
    main() 