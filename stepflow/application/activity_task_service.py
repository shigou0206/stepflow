# stepflow/application/activity_task_service.py

import uuid
from datetime import datetime
from typing import Optional, List
from stepflow.infrastructure.models import ActivityTask
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository

class ActivityTaskService:
    def __init__(self, repo: ActivityTaskRepository):
        # 这里直接注入一个“异步Repo”，而不是Session
        self.repo = repo

    async def schedule_task(
        self,
        run_id: str,
        shard_id: int,
        seq: int,
        activity_type: str,
        input_data: str,
        timeout_seconds: Optional[int] = None,
        retry_policy: Optional[str] = None
    ) -> ActivityTask:
        """
        创建并调度一个新的活动任务, 初始状态为 'scheduled'.
        task_token 通常用UUID, 也可以自定义.
        """
        task_token = str(uuid.uuid4())
        at = ActivityTask(
            task_token=task_token,
            run_id=run_id,
            shard_id=shard_id,
            seq=seq,
            activity_type=activity_type,
            input=input_data,
            status="scheduled",
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy
        )
        return await self.repo.create(at)

    async def start_task(self, task_token: str) -> bool:
        """
        将活动任务状态从 'scheduled' 改为 'running', 并记录开始时间.
        返回 True/False 表示是否成功更新.
        """
        at = await self.repo.get_by_task_token(task_token)
        if not at or at.status != "scheduled":
            return False
        at.status = "running"
        at.started_at = datetime.now()
        await self.repo.update(at)
        return True

    async def complete_task(self, task_token: str, result_data: str) -> bool:
        """
        完成任务, 写入 result, 并更新状态为 'completed'.
        记录完成时间.
        """
        at = await self.repo.get_by_task_token(task_token)
        if not at or at.status != "running":
            return False
        at.status = "completed"
        at.result = result_data
        at.completed_at = datetime.now()
        await self.repo.update(at)
        return True

    async def fail_task(self, task_token: str, result_data: str) -> bool:
        """
        将任务标记为 failed, 记录失败原因/结果.
        """
        at = await self.repo.get_by_task_token(task_token)
        if not at or at.status not in ("running", "scheduled"):
            return False
        at.status = "failed"
        at.result = result_data
        at.completed_at = datetime.now()
        await self.repo.update(at)
        return True

    async def heartbeat_task(self, task_token: str) -> bool:
        """
        更新心跳时间 (heartbeat_at).
        若状态是 running, 则更新heartbeat_at; 否则返回False
        """
        at = await self.repo.get_by_task_token(task_token)
        if not at or at.status != "running":
            return False
        at.heartbeat_at = datetime.now()
        await self.repo.update(at)
        return True

    async def list_tasks_for_run(self, run_id: str) -> List[ActivityTask]:
        return await self.repo.list_by_run_id(run_id)

    async def delete_task(self, task_token: str) -> bool:
        return await self.repo.delete(task_token)