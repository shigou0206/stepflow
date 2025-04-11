#!/usr/bin/env python
# scripts/test_nested_parameters.py

import requests
import json
import uuid
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置 API 基础 URL
BASE_URL = "http://localhost:8000"

def test_nested_parameters():
    """测试多层嵌套参数传递"""
    logger.info("=== 测试多层嵌套参数传递 ===")
    
    # 创建唯一的模板 ID
    unique_id = str(uuid.uuid4())
    template_id = f"nested-params-test-{unique_id}"
    
    # 创建工作流模板 - 包含多层嵌套参数
    template_data = {
        "name": f"多层参数测试-{unique_id}",
        "description": "测试多层嵌套参数传递",
        "template_id": template_id,
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "NestedParametersWorkflow",
            "StartAt": "Level1",
            "States": {
                "Level1": {
                    "Type": "Task",
                    "ActivityType": "ShellTool",
                    "Parameters": {
                        "command": "echo 'Level 1 parameter'",
                        "shell": True,
                        "nested": {
                            "level2": {
                                "value": "This is level 2",
                                "level3": {
                                    "value": "This is level 3"
                                }
                            }
                        }
                    },
                    "ResultPath": "$.level1Result",
                    "Next": "Level2"
                },
                "Level2": {
                    "Type": "Task",
                    "ActivityType": "ShellTool",
                    "Parameters": {
                        "command": "echo 'Using level 2 value: $.level1Result.nested.level2.value'",
                        "shell": True
                    },
                    "ResultPath": "$.level2Result",
                    "Next": "Level3"
                },
                "Level3": {
                    "Type": "Task",
                    "ActivityType": "ShellTool",
                    "Parameters": {
                        "command": "echo 'Using level 3 value: $.level1Result.nested.level2.level3.value'",
                        "shell": True
                    },
                    "ResultPath": "$.level3Result",
                    "End": True
                }
            }
        })
    }
    
    # 创建工作流模板
    logger.info(f"创建工作流模板: {template_id}")
    response = requests.post(f"{BASE_URL}/workflow_templates/", json=template_data)
    if response.status_code != 200:
        logger.error(f"创建模板失败: {response.text}")
        return
    
    # 执行工作流
    execution_data = {
        "template_id": template_id,
        "input": {
            "initialData": "Starting workflow with nested parameters"
        }
    }
    
    logger.info("启动工作流执行")
    response = requests.post(f"{BASE_URL}/workflow_executions/", json=execution_data)
    if response.status_code != 200:
        logger.error(f"启动工作流失败: {response.text}")
        return
    
    run_id = response.json()["run_id"]
    logger.info(f"工作流启动成功，run_id: {run_id}")
    
    # 等待工作流完成
    max_wait = 60  # 最多等待60秒
    execution = None
    
    for i in range(max_wait):
        response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
        if response.status_code != 200:
            logger.error(f"获取工作流状态失败: {response.text}")
            continue
        
        execution = response.json()
        status = execution.get("status")
        logger.info(f"轮询 {i+1}/{max_wait}: 工作流状态 = {status}")
        
        if status in ["completed", "failed", "canceled"]:
            break
        
        time.sleep(1)
    
    if not execution or execution.get("status") != "completed":
        logger.error("工作流未成功完成")
        return
    
    # 获取工作流结果
    logger.info("工作流执行完成，检查结果")
    
    # 获取活动任务
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}/tasks")
    if response.status_code != 200:
        logger.error(f"获取活动任务失败: {response.text}")
        return
    
    tasks = response.json()
    logger.info(f"找到 {len(tasks)} 个活动任务")
    
    # 检查每个任务的结果
    for i, task in enumerate(tasks):
        logger.info(f"任务 {i+1}: {task.get('activity_type')}")
        logger.info(f"状态: {task.get('status')}")
        
        if task.get("input"):
            input_data = json.loads(task.get("input"))
            logger.info(f"输入: {json.dumps(input_data, indent=2)}")
        
        if task.get("result"):
            result_data = json.loads(task.get("result"))
            logger.info(f"结果: {json.dumps(result_data, indent=2)}")
        
        logger.info("---")
    
    # 获取最终工作流状态
    response = requests.get(f"{BASE_URL}/workflow_executions/{run_id}")
    if response.status_code != 200:
        logger.error(f"获取工作流状态失败: {response.text}")
        return
    
    execution = response.json()
    logger.info(f"最终工作流状态: {execution.get('status')}")
    
    # 如果有结果，打印出来
    if execution.get("result"):
        try:
            result_data = json.loads(execution.get("result"))
            logger.info(f"工作流结果: {json.dumps(result_data, indent=2)}")
            
            # 验证结果中包含所有层级的数据
            assert "level1Result" in result_data, "结果中缺少 level1Result"
            assert "level2Result" in result_data, "结果中缺少 level2Result"
            assert "level3Result" in result_data, "结果中缺少 level3Result"
            
            logger.info("测试通过: 多层参数传递成功")
        except json.JSONDecodeError:
            logger.error(f"工作流结果不是有效的 JSON: {execution.get('result')}")
        except AssertionError as e:
            logger.error(f"验证失败: {str(e)}")

if __name__ == "__main__":
    test_nested_parameters() 