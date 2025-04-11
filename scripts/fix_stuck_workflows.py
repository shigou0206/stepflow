#!/usr/bin/env python
# scripts/fix_stuck_workflows.py

import asyncio
import json
import logging
from datetime import datetime, UTC, timedelta
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowExecution, ActivityTask

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def list_stuck_workflows():
    """列出卡住的工作流"""
    logger.info("=== 列出卡住的工作流 ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, and_
        
        # 查找状态为 running 但超过 5 分钟没有更新的工作流
        cutoff_time = datetime.now(UTC) - timedelta(minutes=5)
        stmt = select(WorkflowExecution).where(
            and_(
                WorkflowExecution.status == "running",
                WorkflowExecution.updated_at < cutoff_time
            )
        )
        result = await session.execute(stmt)
        workflows = result.scalars().all()
        
        logger.info(f"找到 {len(workflows)} 个卡住的工作流:")
        for wf in workflows:
            logger.info(f"工作流 ID: {wf.run_id}")
            logger.info(f"  模板 ID: {wf.template_id}")
            logger.info(f"  当前状态: {wf.current_state_name}")
            logger.info(f"  开始时间: {wf.start_time}")
            logger.info(f"  更新时间: {wf.updated_at}")
            
            # 查找该工作流的活动任务
            stmt = select(ActivityTask).where(ActivityTask.run_id == wf.run_id)
            result = await session.execute(stmt)
            tasks = result.scalars().all()
            
            logger.info(f"  找到 {len(tasks)} 个活动任务:")
            for task in tasks:
                logger.info(f"    任务令牌: {task.task_token}")
                logger.info(f"    活动类型: {task.activity_type}")
                logger.info(f"    状态: {task.status}")
                logger.info(f"    调度时间: {task.scheduled_at}")
                logger.info(f"    开始时间: {task.started_at}")
                logger.info(f"    完成时间: {task.completed_at}")
                logger.info("    ---")
            
            logger.info("  ---")

async def cancel_workflow(run_id: str):
    """取消工作流"""
    logger.info(f"=== 取消工作流: {run_id} ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, update
        
        # 获取工作流
        stmt = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
        result = await session.execute(stmt)
        wf = result.scalar_one_or_none()
        
        if not wf:
            logger.error(f"未找到工作流: {run_id}")
            return
        
        if wf.status != "running":
            logger.warning(f"工作流状态不是 running，而是 {wf.status}，无法取消")
            return
        
        # 更新工作流状态
        wf.status = "canceled"
        wf.close_time = datetime.now(UTC)
        wf.updated_at = datetime.now(UTC)
        
        # 取消所有未完成的活动任务
        stmt = select(ActivityTask).where(
            and_(
                ActivityTask.run_id == run_id,
                ActivityTask.status.in_(["scheduled", "running"])
            )
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        for task in tasks:
            task.status = "canceled"
            task.completed_at = datetime.now(UTC)
            task.updated_at = datetime.now(UTC)
        
        # 提交更改
        await session.commit()
        
        logger.info(f"工作流 {run_id} 已取消")
        logger.info(f"已取消 {len(tasks)} 个活动任务")

async def restart_workflow(run_id: str):
    """重启工作流"""
    logger.info(f"=== 重启工作流: {run_id} ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        # 获取工作流
        stmt = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
        result = await session.execute(stmt)
        wf = result.scalar_one_or_none()
        
        if not wf:
            logger.error(f"未找到工作流: {run_id}")
            return
        
        # 获取工作流的输入
        input_data = json.loads(wf.input) if wf.input else {}
        template_id = wf.template_id
        
        # 取消当前工作流
        await cancel_workflow(run_id)
        
        # 创建新的工作流执行请求
        from stepflow.application.workflow_execution_service import WorkflowExecutionService
        from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository
        
        service = WorkflowExecutionService(WorkflowExecutionRepository(session))
        new_wf = await service.start_workflow(template_id, input_data)
        
        logger.info(f"已创建新的工作流执行: {new_wf.run_id}")
        
        return new_wf.run_id

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # 列出卡住的工作流
        asyncio.run(list_stuck_workflows())
    elif len(sys.argv) == 3 and sys.argv[1] == "--cancel":
        # 取消工作流
        run_id = sys.argv[2]
        asyncio.run(cancel_workflow(run_id))
    elif len(sys.argv) == 3 and sys.argv[1] == "--restart":
        # 重启工作流
        run_id = sys.argv[2]
        new_run_id = asyncio.run(restart_workflow(run_id))
        if new_run_id:
            logger.info(f"新的工作流执行 ID: {new_run_id}")
    else:
        print("用法:")
        print("  python fix_stuck_workflows.py              # 列出卡住的工作流")
        print("  python fix_stuck_workflows.py --cancel ID  # 取消工作流")
        print("  python fix_stuck_workflows.py --restart ID # 重启工作流") 