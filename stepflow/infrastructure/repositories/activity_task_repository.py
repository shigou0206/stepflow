# stepflow/infrastructure/repositories/activity_task_repository.py

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from stepflow.infrastructure.models import ActivityTask

class ActivityTaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: ActivityTask) -> ActivityTask:
        """
        插入新的活动任务记录
        """
        self.db.add(task)
        await self.db.commit()       # 提交事务
        await self.db.refresh(task)  # 刷新以获取最新属性(如自增id)
        return task

    async def get_by_task_token(self, task_token: str) -> Optional[ActivityTask]:
        """
        根据 task_token (主键) 获取活动任务
        """
        stmt = select(ActivityTask).where(ActivityTask.task_token == task_token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, task: ActivityTask) -> ActivityTask:
        """
        更新活动任务
        """
        # 确保所有字段都被正确更新
        stmt = (
            update(ActivityTask)
            .where(ActivityTask.task_token == task.task_token)
            .values(
                status=task.status,
                result=task.result,
                error=task.error,  # 确保这里包含 error 字段
                error_details=task.error_details,
                started_at=task.started_at,
                completed_at=task.completed_at,
                # 其他需要更新的字段...
            )
            .execution_options(synchronize_session="fetch")
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        # 返回更新后的任务
        return await self.get_by_token(task.task_token)

    async def delete(self, task_token: str) -> bool:
        """
        根据 task_token 删除对应记录, 返回是否成功
        """
        obj = await self.get_by_task_token(task_token)
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True

    async def list_by_run_id(self, run_id: str) -> List[ActivityTask]:
        """
        列出同一个工作流实例下的全部活动任务
        """
        stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_status(self, status: str) -> List[ActivityTask]:
        """
        列出所有指定状态的活动任务
        """
        stmt = select(ActivityTask).where(ActivityTask.status == status)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_token(self, task_token: str) -> Optional[ActivityTask]:
        """根据任务令牌获取任务"""
        stmt = select(ActivityTask).where(ActivityTask.task_token == task_token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> List[ActivityTask]:
        """列出所有活动任务"""
        result = await self.db.execute(select(ActivityTask))
        return result.scalars().all()

    async def get_by_run_id(self, run_id: str) -> List[ActivityTask]:
        """获取工作流执行的所有活动任务"""
        stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_status(self, status: str, limit: int = 10) -> List[ActivityTask]:
        """获取指定状态的活动任务"""
        stmt = select(ActivityTask).where(ActivityTask.status == status).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_status(self, task_token: str, status: str) -> None:
        """更新活动任务状态"""
        stmt = (
            update(ActivityTask)
            .where(ActivityTask.task_token == task_token)
            .values(status=status)
        )
        await self.db.execute(stmt)

    async def save(self, task: ActivityTask) -> None:
        """保存活动任务"""
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)