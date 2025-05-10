import uuid
from datetime import datetime, UTC
from typing import Optional, List
from stepflow.persistence.models import ActivityTask
from stepflow.persistence.repositories.activity_task_repository import ActivityTaskRepository

class ActivityTaskService:
    def __init__(self, repo: ActivityTaskRepository):
        self.repo = repo

    async def create_task(self, run_id: str, activity_type: str, input_data: str) -> ActivityTask:
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
        return await self.repo.get_by_task_token(task_token)

    async def get_tasks_by_run_id(self, run_id: str) -> List[ActivityTask]:
        return await self.repo.list_by_run_id(run_id)

    async def get_scheduled_tasks(self, limit: int = 10) -> List[ActivityTask]:
        return await self.repo.list_by_status("scheduled", limit)

    async def mark_tasks_as_running(self, task_tokens: List[str]) -> None:
        for token in task_tokens:
            await self.repo.update_status(token, "running")

    async def start_task(self, task_token: str) -> Optional[ActivityTask]:
        task = await self.repo.get_by_task_token(task_token)
        if not task:
            raise ValueError(f"Task with token {task_token} not found")
        task.started_at = datetime.now(UTC)
        task.status = "running"
        return await self.repo.update_full(task)

    async def complete_task(self, task_token: str, result_data: str) -> Optional[ActivityTask]:
        task = await self.repo.get_by_task_token(task_token)
        if not task:
            raise ValueError(f"Task with token {task_token} not found")
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        task.result = result_data
        return await self.repo.update_full(task)

    async def fail_task(self, task_token: str, reason: str, details: str = None) -> Optional[ActivityTask]:
        task = await self.repo.get_by_task_token(task_token)
        if not task:
            raise ValueError(f"Task with token {task_token} not found")
        task.status = "failed"
        task.completed_at = datetime.now(UTC)
        task.error = reason
        task.error_details = details
        return await self.repo.update_full(task)

    async def heartbeat_task(self, task_token: str, details: Optional[str] = None) -> Optional[ActivityTask]:
        task = await self.repo.get_by_task_token(task_token)
        if not task or task.status != "running":
            return None
        task.last_heartbeat_at = datetime.now(UTC)
        if details:
            task.heartbeat_details = details
        return await self.repo.update_full(task)

    async def cancel_task(self, task_token: str) -> Optional[ActivityTask]:
        task = await self.repo.get_by_task_token(task_token)
        if not task or task.status not in ["scheduled", "running"]:
            return None
        task.status = "canceled"
        task.completed_at = datetime.now(UTC)
        return await self.repo.update_full(task)

    async def list_tasks_by_status(self, status: str) -> List[ActivityTask]:
        return await self.repo.list_by_status(status)

    async def delete_task(self, task_token: str) -> bool:
        return await self.repo.delete(task_token)