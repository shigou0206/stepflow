# stepflow/worker/activity_worker.py

import asyncio
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import ActivityTask
from stepflow.domain.engine.execution_engine import advance_workflow
from .tools.tool_registry import tool_registry

async def run_activity_worker():
    """
    周期性扫描 DB 中 status='scheduled' 的 ActivityTask, 执行后写 status='completed'
    并调用 advance_workflow(run_id) 来推动工作流.
    """
    while True:
        # 1) 取 "scheduled" tasks
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ActivityTask).where(ActivityTask.status == 'scheduled')
            )
            tasks = result.scalars().all()

            # 2) 标记为running
            for t in tasks:
                t.status = 'running'
            await session.commit()

        # 3) 逐个执行
        for task in tasks:
            activity_type = task.activity_type
            tool = tool_registry.get(activity_type)
            if not tool:
                # 未知类型 => fail
                await mark_task_failed(task, reason=f"Unknown activity_type: {activity_type}")
                continue

            # 解析 input
            input_data = {}
            if task.input:
                input_data = json.loads(task.input)

            try:
                # run tool
                result_data = await tool.run(input_data)

                # 更新DB => completed
                await mark_task_completed(task, result_data)

                # 通知引擎 => 让 workflow 往下走
                await call_advance_workflow(task.run_id)

            except Exception as e:
                # 出错 => fail
                await mark_task_failed(task, reason=str(e))

        # 4) 间隔轮询
        await asyncio.sleep(5)


async def mark_task_completed(task: ActivityTask, result_data: dict):
    async with AsyncSessionLocal() as session:
        db_task = await session.get(ActivityTask, task.task_token)
        if db_task:
            db_task.status = 'completed'
            db_task.result = json.dumps(result_data)
            db_task.completed_at = datetime.utcnow()
            await session.commit()

async def mark_task_failed(task: ActivityTask, reason: str):
    async with AsyncSessionLocal() as session:
        db_task = await session.get(ActivityTask, task.task_token)
        if db_task:
            db_task.status = 'failed'
            db_task.result = json.dumps({"error": reason})
            db_task.completed_at = datetime.utcnow()
            await session.commit()

async def call_advance_workflow(run_id: str):
    """
    让引擎推进下一个节点.  Typically, we do:
      advance_workflow(session, run_id)
    """
    async with AsyncSessionLocal() as session:
        await advance_workflow(session, run_id)