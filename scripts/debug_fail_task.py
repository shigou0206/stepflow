#!/usr/bin/env python
# scripts/debug_fail_task.py

import asyncio
import uuid
from datetime import datetime, UTC
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.application.activity_task_service import ActivityTaskService
from stepflow.infrastructure.models import ActivityTask

async def debug_fail_task():
    """调试 fail_task 方法"""
    print("=== 调试 fail_task 方法 ===")
    
    async with AsyncSessionLocal() as session:
        # 创建仓库和服务
        repo = ActivityTaskRepository(session)
        service = ActivityTaskService(repo)
        
        # 创建一个测试任务
        task_token = str(uuid.uuid4())
        task = ActivityTask(
            task_token=task_token,
            run_id="debug-run",
            shard_id=0,
            seq=1,
            activity_type="debug_activity",
            input="{}",
            status="running"
        )
        
        # 保存任务
        created_task = await repo.create(task)
        print(f"创建任务: {created_task.task_token}, 状态: {created_task.status}")
        
        # 标记任务失败
        reason = "Debug failure reason"
        details = "Debug failure details"
        print(f"标记任务失败, 原因: {reason}")
        
        failed_task = await service.fail_task(task_token, reason, details)
        
        # 检查结果
        print(f"任务状态: {failed_task.status}")
        print(f"完成时间: {failed_task.completed_at}")
        print(f"错误信息: {failed_task.error}")
        print(f"错误详情: {failed_task.error_details}")
        
        # 直接从数据库再次获取任务，确认所有字段都被正确保存
        db_task = await repo.get_by_token(task_token)
        print("\n从数据库重新获取任务:")
        print(f"任务状态: {db_task.status}")
        print(f"完成时间: {db_task.completed_at}")
        print(f"错误信息: {db_task.error}")
        print(f"错误详情: {db_task.error_details}")

if __name__ == "__main__":
    asyncio.run(debug_fail_task()) 