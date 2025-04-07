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
        return await self.repo.list_by_run_id(run_id)

    async def start_task(self, task_token: str) -> Optional[ActivityTask]:
        """开始一个活动任务"""
        task = await self.repo.get_by_token(task_token)
        if not task or task.status != "scheduled":
            return None
        
        task.status = "running"
        task.started_at = datetime.now(UTC)
        return await self.repo.update(task)

    async def complete_task(self, task_token: str, result_data: str) -> Optional[ActivityTask]:
        """完成一个活动任务并发送 WebSocket 通知"""
        task = await self.repo.get_by_token(task_token)
        if not task or task.status != "running":
            return None
        
        task.status = "completed"
        task.result = result_data
        task.completed_at = datetime.now(UTC)
        updated_task = await self.repo.update(task)
        
        # 发送 WebSocket 通知
        await manager.send_to_workflow(task.run_id, {
            "type": "task_completed",
            "run_id": task.run_id,
            "task_token": task_token,
            "activity_type": task.activity_type,
            "timestamp": datetime.now(UTC).isoformat()
        })
        
        return updated_task

    async def fail_task(self, task_token: str, reason: str, details: Optional[str] = None) -> Optional[ActivityTask]:
        """标记一个活动任务为失败，更新工作流状态，并发送 WebSocket 通知"""
        task = await self.repo.get_by_token(task_token)
        if not task or task.status != "running":
            return None
        
        task.status = "failed"
        task.result = f"Failed: {reason}"
        if details:
            task.result += f" - Details: {details}"
        task.completed_at = datetime.now(UTC)
        
        # 更新任务状态
        updated_task = await self.repo.update(task)
        
        # 发送 WebSocket 通知
        await manager.send_to_workflow(task.run_id, {
            "type": "task_failed",
            "run_id": task.run_id,
            "task_token": task_token,
            "activity_type": task.activity_type,
            "reason": reason,
            "timestamp": datetime.now(UTC).isoformat()
        })
        
        # 通知执行引擎任务失败
        # 使用延迟导入避免循环依赖
        from stepflow.domain.engine.execution_engine import handle_activity_task_failed
        await handle_activity_task_failed(task_token, reason, details)
        
        return updated_task

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