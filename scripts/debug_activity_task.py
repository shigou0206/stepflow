#!/usr/bin/env python
# scripts/debug_activity_task.py

import asyncio
import json
import logging
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import ActivityTask

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_activity_task(task_token: str):
    """调试活动任务"""
    logger.info(f"=== 调试活动任务: {task_token} ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        stmt = select(ActivityTask).where(ActivityTask.task_token == task_token)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            logger.error(f"未找到活动任务: {task_token}")
            return
        
        # 打印任务信息
        logger.info(f"任务令牌: {task.task_token}")
        logger.info(f"运行 ID: {task.run_id}")
        logger.info(f"活动类型: {task.activity_type}")
        logger.info(f"状态: {task.status}")
        logger.info(f"调度时间: {task.scheduled_at}")
        logger.info(f"开始时间: {task.started_at}")
        logger.info(f"完成时间: {task.completed_at}")
        
        # 打印输入
        if task.input:
            try:
                input_data = json.loads(task.input)
                logger.info(f"输入: {json.dumps(input_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error(f"输入不是有效的 JSON: {task.input}")
        else:
            logger.info("输入为空")
        
        # 打印结果
        if task.result:
            try:
                result_data = json.loads(task.result)
                logger.info(f"结果: {json.dumps(result_data, indent=2)}")
            except json.JSONDecodeError:
                logger.error(f"结果不是有效的 JSON: {task.result}")
        else:
            logger.info("结果为空")
        
        # 打印错误信息
        if task.error:
            logger.info(f"错误: {task.error}")
        else:
            logger.info("错误为空")
        
        # 打印错误详情
        if task.error_details:
            logger.info(f"错误详情: {task.error_details}")
        else:
            logger.info("错误详情为空")
        
        # 直接查看数据库中的原始字段
        logger.info("=== 数据库中的原始字段 ===")
        for column in task.__table__.columns:
            value = getattr(task, column.name)
            logger.info(f"{column.name}: {value}")

async def debug_tasks_by_run_id(run_id: str):
    """调试工作流执行的所有活动任务"""
    logger.info(f"=== 调试工作流执行的活动任务: {run_id} ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        logger.info(f"找到 {len(tasks)} 个活动任务:")
        for task in tasks:
            logger.info(f"  任务令牌: {task.task_token}")
            logger.info(f"  活动类型: {task.activity_type}")
            logger.info(f"  状态: {task.status}")
            
            # 打印错误信息
            if task.error:
                logger.info(f"  错误: {task.error}")
            else:
                logger.info("  错误为空")
            
            # 打印错误详情
            if task.error_details:
                logger.info(f"  错误详情: {task.error_details}")
            else:
                logger.info("  错误详情为空")
            
            logger.info("  ---")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python debug_activity_task.py <task_token>  # 调试指定任务")
        print("  python debug_activity_task.py --run <run_id>  # 调试工作流执行的所有任务")
        sys.exit(1)
    
    if sys.argv[1] == "--run" and len(sys.argv) == 3:
        run_id = sys.argv[2]
        asyncio.run(debug_tasks_by_run_id(run_id))
    else:
        task_token = sys.argv[1]
        asyncio.run(debug_activity_task(task_token)) 