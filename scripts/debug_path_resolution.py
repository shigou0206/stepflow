#!/usr/bin/env python
# scripts/debug_path_resolution.py

import asyncio
import json
import logging
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowExecution, ActivityTask
from stepflow.domain.engine.path_utils import get_value_by_path, set_value_by_path, resolve_path_references

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_path_resolution(run_id: str):
    """调试路径解析和参数替换"""
    logger.info(f"=== 调试路径解析: {run_id} ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        # 获取工作流执行
        stmt = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
        result = await session.execute(stmt)
        wf_exec = result.scalar_one_or_none()
        
        if not wf_exec:
            logger.error(f"未找到工作流执行: {run_id}")
            return
        
        logger.info(f"工作流状态: {wf_exec.status}")
        logger.info(f"当前状态: {wf_exec.current_state_name}")
        
        # 解析备忘录
        memo = json.loads(wf_exec.memo) if wf_exec.memo else {}
        logger.info(f"工作流备忘录: {json.dumps(memo, indent=2)}")
        
        # 获取活动任务
        stmt = select(ActivityTask).where(ActivityTask.run_id == run_id).order_by(ActivityTask.scheduled_at)
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        logger.info(f"找到 {len(tasks)} 个活动任务:")
        for i, task in enumerate(tasks):
            logger.info(f"任务 {i+1}: {task.activity_type}")
            logger.info(f"  状态: {task.status}")
            logger.info(f"  调度时间: {task.scheduled_at}")
            logger.info(f"  开始时间: {task.started_at}")
            logger.info(f"  完成时间: {task.completed_at}")
            
            # 解析输入
            if task.input:
                try:
                    input_data = json.loads(task.input)
                    logger.info(f"  输入: {json.dumps(input_data, indent=2)}")
                    
                    # 测试路径解析
                    if isinstance(input_data, dict) and 'command' in input_data:
                        command = input_data['command']
                        logger.info(f"  命令: {command}")
                        
                        # 尝试解析命令中的路径引用
                        if isinstance(command, str) and '$.' in command:
                            logger.info("  尝试解析命令中的路径引用:")
                            resolved_command = resolve_path_references(command, memo)
                            logger.info(f"  解析后的命令: {resolved_command}")
                except json.JSONDecodeError:
                    logger.error(f"  输入不是有效的 JSON: {task.input}")
            
            # 解析结果
            if task.result:
                try:
                    result_data = json.loads(task.result)
                    logger.info(f"  结果: {json.dumps(result_data, indent=2)}")
                except json.JSONDecodeError:
                    logger.error(f"  结果不是有效的 JSON: {task.result}")
            
            logger.info("  ---")
        
        # 测试路径解析函数
        logger.info("=== 测试路径解析函数 ===")
        
        # 测试数据
        test_data = {
            "user": {
                "name": "Claude",
                "role": "Assistant"
            },
            "level1Result": {
                "nested": {
                    "level2": {
                        "value": "This is level 2",
                        "level3": {
                            "value": "This is level 3"
                        }
                    }
                }
            }
        }
        
        # 测试路径获取
        paths_to_test = [
            "$.user.name",
            "$.level1Result.nested.level2.value",
            "$.level1Result.nested.level2.level3.value",
            "$.non_existent_path"
        ]
        
        for path in paths_to_test:
            value = get_value_by_path(test_data, path)
            logger.info(f"路径 '{path}' 的值: {value}")
        
        # 测试路径引用解析
        references_to_test = [
            "Hello, $.user.name!",
            "Level 2 value: $.level1Result.nested.level2.value",
            "Level 3 value: $.level1Result.nested.level2.level3.value",
            "Missing path: $.non_existent_path"
        ]
        
        for ref in references_to_test:
            resolved = resolve_path_references(ref, test_data)
            logger.info(f"引用 '{ref}' 解析为: '{resolved}'")

async def debug_workflow_state(run_id: str):
    """调试工作流状态"""
    logger.info(f"=== 调试工作流状态: {run_id} ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        # 获取工作流执行
        stmt = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
        result = await session.execute(stmt)
        wf_exec = result.scalar_one_or_none()
        
        if not wf_exec:
            logger.error(f"未找到工作流执行: {run_id}")
            return
        
        # 打印工作流状态
        logger.info(f"工作流 ID: {wf_exec.run_id}")
        logger.info(f"模板 ID: {wf_exec.template_id}")
        logger.info(f"状态: {wf_exec.status}")
        logger.info(f"当前状态: {wf_exec.current_state_name}")
        logger.info(f"开始时间: {wf_exec.start_time}")
        logger.info(f"结束时间: {wf_exec.close_time}")
        
        # 解析备忘录
        if wf_exec.memo:
            try:
                memo_data = json.loads(wf_exec.memo)
                logger.info(f"备忘录: {json.dumps(memo_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error(f"备忘录不是有效的 JSON: {wf_exec.memo}")
        else:
            logger.info("备忘录为空")
        
        # 解析结果
        if wf_exec.result:
            try:
                result_data = json.loads(wf_exec.result)
                logger.info(f"结果: {json.dumps(result_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error(f"结果不是有效的 JSON: {wf_exec.result}")
        else:
            logger.info("结果为空")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python debug_path_resolution.py <run_id>")
        sys.exit(1)
    
    run_id = sys.argv[1]
    asyncio.run(debug_path_resolution(run_id))
    asyncio.run(debug_workflow_state(run_id)) 