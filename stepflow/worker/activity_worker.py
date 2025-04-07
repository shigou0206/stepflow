# stepflow/worker/activity_worker.py

import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List
import traceback
import os

from sqlalchemy import select
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import ActivityTask
from stepflow.application.activity_task_service import ActivityTaskService
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.domain.engine.execution_engine import advance_workflow
from .tools.tool_registry import tool_registry

logger = logging.getLogger(__name__)

# 配置并行处理的任务数量
MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "10"))

async def run_activity_worker():
    """
    周期性扫描 DB 中 status='scheduled' 的 ActivityTask, 并行执行任务
    """
    logger.info(f"活动工作器启动，最大并行任务数: {MAX_CONCURRENT_TASKS}")
    
    while True:
        try:
            # 1) 取 "scheduled" tasks
            tasks = await get_scheduled_tasks()
            
            if tasks:
                logger.info(f"找到 {len(tasks)} 个待处理的活动任务")
                
                # 2) 标记为running
                await mark_tasks_as_running(tasks)
                
                # 3) 并行执行任务
                await process_tasks_concurrently(tasks)
            
        except Exception as e:
            logger.exception(f"活动工作器循环中发生错误: {str(e)}")
        
        # 4) 间隔轮询
        await asyncio.sleep(5)

async def get_scheduled_tasks(limit: int = MAX_CONCURRENT_TASKS) -> List[ActivityTask]:
    """获取待处理的任务，限制数量以控制并行度"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ActivityTask)
            .where(ActivityTask.status == 'scheduled')
            .limit(limit)
        )
        return result.scalars().all()

async def mark_tasks_as_running(tasks: List[ActivityTask]) -> None:
    """将任务标记为运行中"""
    async with AsyncSessionLocal() as session:
        for task in tasks:
            # 重新获取任务以避免会话问题
            db_task = await session.get(ActivityTask, task.task_token)
            if db_task and db_task.status == 'scheduled':
                db_task.status = 'running'
                db_task.started_at = datetime.now(UTC)
        await session.commit()

async def process_tasks_concurrently(tasks: List[ActivityTask]) -> None:
    """并行处理多个任务"""
    # 创建任务协程列表
    coroutines = [process_activity_task(task) for task in tasks]
    
    # 使用 gather 并行执行所有任务
    await asyncio.gather(*coroutines, return_exceptions=True)

async def process_activity_task(task: ActivityTask):
    """处理单个活动任务"""
    logger.info(f"处理活动任务: {task.task_token}, 类型: {task.activity_type}")
    
    # 创建服务和仓库
    async with AsyncSessionLocal() as session:
        repo = ActivityTaskRepository(session)
        service = ActivityTaskService(repo)
        
        # 重新获取任务以确保状态最新
        task = await repo.get_by_token(task.task_token)
        if not task or task.status != "running":
            logger.warning(f"任务 {task.task_token} 状态不是 running，跳过处理")
            return
        
        activity_type = task.activity_type
        tool = tool_registry.get(activity_type)
        
        if not tool:
            # 未知类型 => 标记为失败
            logger.error(f"未找到活动类型 {activity_type} 的工具")
            await service.fail_task(
                task.task_token, 
                reason=f"Unknown activity type: {activity_type}"
            )
            return

        # 解析输入数据
        input_data = {}
        if task.input:
            try:
                input_data = json.loads(task.input)
            except json.JSONDecodeError as e:
                logger.error(f"解析任务输入数据失败: {str(e)}")
                await service.fail_task(
                    task.task_token, 
                    reason=f"Invalid input data: {str(e)}"
                )
                return

        try:
            # 执行工具
            result_data = await tool.run(input_data)
            
            # 检查工具执行结果是否包含错误
            if isinstance(result_data, dict) and (result_data.get("error") or result_data.get("ok") is False):
                # 如果工具执行失败，标记任务为失败
                error_message = result_data.get("error", "Unknown error")
                logger.warning(f"工具执行失败: {error_message}")
                await service.fail_task(
                    task.task_token, 
                    reason=f"Tool execution failed: {error_message}",
                    details=json.dumps(result_data)
                )
            else:
                # 工具执行成功，完成任务
                logger.info(f"工具执行成功，完成任务 {task.task_token}")
                await service.complete_task(
                    task.task_token,
                    result_data=json.dumps(result_data)
                )
                
                # 通知引擎 => 让 workflow 往下走
                await call_advance_workflow(task.run_id)

        except Exception as e:
            logger.exception(f"处理活动任务 {task.task_token} 时出错: {str(e)}")
            # 标记任务为失败
            await service.fail_task(
                task.task_token,
                reason=f"Exception during task execution: {str(e)}",
                details=traceback.format_exc()
            )

async def call_advance_workflow(run_id: str):
    """让引擎推进下一个节点"""
    try:
        async with AsyncSessionLocal() as session:
            await advance_workflow(session, run_id)
    except Exception as e:
        logger.exception(f"推进工作流 {run_id} 时出错: {str(e)}")