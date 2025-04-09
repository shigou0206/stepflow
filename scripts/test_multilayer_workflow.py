#!/usr/bin/env python
# scripts/test_multilayer_workflow.py

import requests
import json
import time
import sys
import uuid
import websockets
import asyncio
from datetime import datetime

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

def create_workflow_template():
    """创建一个多层工作流模板"""
    template_id = f"multilayer-workflow-{uuid.uuid4()}"
    
    # 定义一个包含4层的工作流
    workflow_dsl = {
        "Version": "1.0",
        "Name": "MultilayerDataProcessingWorkflow",
        "StartAt": "FetchData",
        "States": {
            # 第一层：数据获取
            "FetchData": {
                "Type": "Task",
                "ActivityType": "HttpTool",
                "Parameters": {
                    "url": "https://jsonplaceholder.typicode.com/posts/1",
                    "method": "GET",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "timeout": 10
                },
                "ResultPath": "$.data",
                "Next": "TransformData"
            },
            
            # 第二层：数据转换
            "TransformData": {
                "Type": "Task",
                "ActivityType": "ShellTool",
                "Parameters": {
                    "command": "echo '转换数据' && sleep 2",
                    "timeout": 5
                },
                "ResultPath": "$.transformed",
                "Next": "CheckDataQuality"
            },
            
            # 第三层：数据分析
            "CheckDataQuality": {
                "Type": "Choice",
                "Choices": [
                    {
                        "Variable": "$.data.status",
                        "NumericEquals": 200,
                        "Next": "AnalyzeData"
                    }
                ],
                "Default": "HandleError"
            },
            
            # 数据分析子流程
            "AnalyzeData": {
                "Type": "Task",
                "ActivityType": "ShellTool",
                "Parameters": {
                    "command": "echo '分析数据' && sleep 3",
                    "timeout": 10
                },
                "ResultPath": "$.analysis",
                "Next": "NotifySuccess"
            },
            
            # 错误处理
            "HandleError": {
                "Type": "Task",
                "ActivityType": "ShellTool",
                "Parameters": {
                    "command": "echo '处理错误' && sleep 1",
                    "timeout": 5
                },
                "ResultPath": "$.error_handling",
                "Next": "NotifyFailure"
            },
            
            # 第四层：成功通知
            "NotifySuccess": {
                "Type": "Task",
                "ActivityType": "HttpTool",
                "Parameters": {
                    "url": "https://httpbin.org/post",
                    "method": "POST",
                    "json": {
                        "status": "success",
                        "message": "数据处理成功",
                        "timestamp": "${datetime.now().isoformat()}"
                    },
                    "timeout": 5
                },
                "ResultPath": "$.notification",
                "End": True
            },
            
            # 第四层：失败通知
            "NotifyFailure": {
                "Type": "Task",
                "ActivityType": "HttpTool",
                "Parameters": {
                    "url": "https://httpbin.org/post",
                    "method": "POST",
                    "json": {
                        "status": "failure",
                        "message": "数据处理失败",
                        "timestamp": "${datetime.now().isoformat()}"
                    },
                    "timeout": 5
                },
                "ResultPath": "$.notification",
                "End": True
            }
        }
    }
    
    # 创建工作流模板
    template_data = {
        "name": "多层数据处理工作流",
        "description": "一个包含数据获取、转换、分析和通知四个层次的工作流",
        "template_id": template_id,
        "dsl_definition": json.dumps(workflow_dsl)
    }
    
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        print(f"创建工作流模板失败: {response.text}")
        return None
    
    print(f"创建工作流模板成功: {template_id}")
    return template_id

def start_workflow(template_id):
    """启动工作流执行"""
    workflow_data = {
        "template_id": template_id,
        "input": {
            "timestamp": datetime.now().isoformat(),
            "requestId": str(uuid.uuid4())
        }
    }
    
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=workflow_data)
    if response.status_code != 200:
        print(f"启动工作流失败: {response.text}")
        return None
    
    result = response.json()
    run_id = result.get("run_id")
    print(f"启动工作流成功，run_id: {run_id}")
    return run_id

async def monitor_workflow(run_id):
    """通过 WebSocket 监控工作流执行"""
    url = f"ws://localhost:8000/ws/status?workflow_id={run_id}"
    print(f"连接到工作流 {run_id} 的 WebSocket...")
    
    try:
        async with websockets.connect(url, ping_interval=None, close_timeout=60) as websocket:
            print("WebSocket 连接已建立")
            
            # 接收初始连接消息
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"收到连接消息: {response}")
            
            # 监控工作流状态
            completed = False
            while not completed:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(message)
                    print(f"收到工作流更新: {json.dumps(data, indent=2)}")
                    
                    # 检查工作流是否完成
                    if data.get("type") == "status_update" and data.get("status") in ["completed", "failed", "canceled"]:
                        completed = True
                        print(f"工作流执行已{data.get('status')}")
                        
                except asyncio.TimeoutError:
                    # 发送 ping 保持连接
                    print("等待消息超时，发送 ping...")
                    await websocket.ping()
                    
                    # 同时检查 API 获取最新状态
                    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
                    if response.status_code == 200:
                        status = response.json().get("status")
                        if status in ["completed", "failed", "canceled"]:
                            completed = True
                            print(f"工作流执行已{status}")
    
    except Exception as e:
        print(f"监控工作流时出错: {str(e)}")
        import traceback
        traceback.print_exc()

def check_workflow_result(run_id):
    """检查工作流执行结果"""
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    if response.status_code != 200:
        print(f"获取工作流执行结果失败: {response.text}")
        return None
    
    result = response.json()
    print(f"工作流执行结果:")
    print(json.dumps(result, indent=2))
    
    # 获取工作流事件历史
    response = requests.get(f"{BASE_URL}/workflow_events/{run_id}")
    if response.status_code == 200:
        events = response.json()
        print(f"工作流事件历史:")
        for event in events:
            print(f"- {event.get('event_type')} ({event.get('created_at')})")
    
    return result

async def main():
    """主函数"""
    print("===== 开始测试多层工作流 =====")
    
    # 1. 创建工作流模板
    template_id = create_workflow_template()
    if not template_id:
        return
    
    # 2. 启动工作流
    run_id = start_workflow(template_id)
    if not run_id:
        return
    
    # 3. 监控工作流执行
    await monitor_workflow(run_id)
    
    # 4. 检查工作流结果
    result = check_workflow_result(run_id)
    
    print("===== 多层工作流测试完成 =====")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("测试被用户中断") 