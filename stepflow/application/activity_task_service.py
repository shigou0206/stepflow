# stepflow/application/activity_task_service.py

import uuid
from datetime import datetime, UTC
from typing import Optional, List
from stepflow.infrastructure.models import ActivityTask
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.interfaces.websocket.connection_manager import manager

class ActivityTaskService:
    def __init__(self, repo: ActivityTaskRepository):
        # 这里直接注入一个"异步Repo"，而不是Session
        self.repo = repo

    async def create_task(self, run_id: str, activity_type: str, input_data: str) -> ActivityTask:
        """创建一个新的活动任务"""
        task = ActivityTask(
            task_token=str(uuid.uuid4()),
            run_id=run_id,
            activity_type=activity_type,
            status="scheduled",
            input=input_data,
            scheduled_at=datetime.now(UTC)
        )
        return await self.repo.create(task)

    async def get_task(self, task_token: str) -> Optional[ActivityTask]:
        """获取活动任务"""
        return await self.repo.get_by_token(task_token)

    async def get_tasks_by_run_id(self, run_id: str) -> List[ActivityTask]:
        """获取特定工作流执行的所有活动任务"""
        return await self.repo.get_by_run_id(run_id)

    async def get_scheduled_tasks(self, limit: int = 10) -> List[ActivityTask]:
        """获取待处理的任务"""
        return await self.repo.get_by_status("scheduled", limit)

    async def mark_tasks_as_running(self, task_tokens: List[str]) -> None:
        """标记任务为运行中"""
        for token in task_tokens:
            await self.repo.update_status(token, "running")

    async def start_task(self, task_token: str) -> None:
        """标记任务为开始执行"""
        task = await self.repo.get_by_token(task_token)
        if not task:
            raise ValueError(f"Task with token {task_token} not found")
        
        task.started_at = datetime.now(UTC)
        await self.repo.save(task)

    async def complete_task(self, task_token: str, result_data: str) -> None:
        """标记任务为完成"""
        task = await self.repo.get_by_token(task_token)
        if not task:
            raise ValueError(f"Task with token {task_token} not found")
        
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        task.result = result_data
        await self.repo.save(task)

    async def fail_task(self, task_token: str, reason: str, details: str = None) -> None:
        """标记任务为失败"""
        task = await self.repo.get_by_token(task_token)
        if not task:
            raise ValueError(f"Task with token {task_token} not found")
        
        task.status = "failed"
        task.completed_at = datetime.now(UTC)
        task.error = reason  # 确保错误原因被保存
        task.error_details = details  # 确保错误详情被保存
        await self.repo.save(task)

    async def heartbeat_task(self, task_token: str, details: Optional[str] = None) -> Optional[ActivityTask]:
        """更新活动任务心跳"""
        task = await self.repo.get_by_token(task_token)
        if not task or task.status != "running":
            return None
        
        task.last_heartbeat_at = datetime.now(UTC)
        if details:
            task.heartbeat_details = details
        return await self.repo.update(task)

    async def cancel_task(self, task_token: str) -> Optional[ActivityTask]:
        """取消一个活动任务"""
        task = await self.repo.get_by_token(task_token)
        if not task or task.status not in ["scheduled", "running"]:
            return None
        
        task.status = "canceled"
        task.completed_at = datetime.now(UTC)
        return await self.repo.update(task)

    async def list_tasks_by_status(self, status: str) -> List[ActivityTask]:
        """列出特定状态的活动任务"""
        return await self.repo.list_by_status(status)

    async def delete_task(self, task_token: str) -> bool:
        return await self.repo.delete(task_token)