#!/usr/bin/env python
# scripts/debug_workflow_status.py

import asyncio
import json
import logging
from datetime import datetime
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowExecution, ActivityTask

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_workflow_status(run_id: str):
    """调试工作流执行状态"""
    logger.info(f"=== 调试工作流状态: {run_id} ===")
    
    async with AsyncSessionLocal() as session:
        # 查询工作流执行
        from sqlalchemy import select
        
        stmt = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
        result = await session.execute(stmt)
        wf_exec = result.scalar_one_or_none()
        
        if not wf_exec:
            logger.error(f"未找到工作流执行: {run_id}")
            return
        
        # 打印工作流状态
        logger.info(f"工作流状态: {wf_exec.status}")
        logger.info(f"当前状态名称: {wf_exec.current_state_name}")
        logger.info(f"开始时间: {wf_exec.start_time}")
        logger.info(f"结束时间: {wf_exec.close_time}")
        
        # 打印工作流结果
        if wf_exec.result:
            try:
                result_data = json.loads(wf_exec.result)
                logger.info(f"工作流结果: {json.dumps(result_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error(f"工作流结果不是有效的 JSON: {wf_exec.result}")
        else:
            logger.info("工作流结果为空")
        
        # 查询活动任务
        stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        logger.info(f"找到 {len(tasks)} 个活动任务:")
        for task in tasks:
            logger.info(f"  任务令牌: {task.task_token}")
            logger.info(f"  活动类型: {task.activity_type}")
            logger.info(f"  状态: {task.status}")
            logger.info(f"  调度时间: {task.scheduled_at}")
            logger.info(f"  开始时间: {task.started_at}")
            logger.info(f"  完成时间: {task.completed_at}")
            
            if task.error:
                logger.info(f"  错误: {task.error}")
                if task.error_details:
                    logger.info(f"  错误详情: {task.error_details}")
            
            if task.result:
                try:
                    result_data = json.loads(task.result)
                    logger.info(f"  任务结果: {json.dumps(result_data, indent=2)}")
                except json.JSONDecodeError:
                    logger.error(f"  任务结果不是有效的 JSON: {task.result}")
            
            logger.info("  ---")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python debug_workflow_status.py <run_id>")
        sys.exit(1)
    
    run_id = sys.argv[1]
    asyncio.run(debug_workflow_status(run_id)) 