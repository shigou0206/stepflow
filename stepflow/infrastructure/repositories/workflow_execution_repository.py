# stepflow/infrastructure/repositories/workflow_execution_repository.py

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from stepflow.infrastructure.models import WorkflowExecution

class WorkflowExecutionRepository:
    def __init__(self, db: AsyncSession):
        """db: AsyncSession, 由外部(比如Service或依赖注入)提供"""
        self.db = db

    async def create(self, wf_exec: WorkflowExecution) -> WorkflowExecution:
        """插入新的工作流执行记录"""
        self.db.add(wf_exec)
        await self.db.commit()
        await self.db.refresh(wf_exec)
        return wf_exec

    async def get_by_run_id(self, run_id: str) -> Optional[WorkflowExecution]:
        """根据 run_id 获取工作流执行, 不存在则返回 None"""
        stmt = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, wf_exec: WorkflowExecution) -> WorkflowExecution:
        """
        当外部已经拿到了 wf_exec, 并修改(如status=...),
        调用本方法执行 commit & refresh.
        """
        await self.db.commit()
        await self.db.refresh(wf_exec)
        return wf_exec

    async def delete(self, run_id: str) -> bool:
        """
        根据 run_id 删除对应的工作流执行, 返回是否删除成功
        """
        obj = await self.get_by_run_id(run_id)
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True

    async def list_all(self) -> List[WorkflowExecution]:
        """列出所有工作流执行(仅适合小规模, 大规模需分页)"""
        stmt = select(WorkflowExecution)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_status(self, status: str) -> List[WorkflowExecution]:
        """按状态查询列表"""
        stmt = select(WorkflowExecution).where(WorkflowExecution.status == status)
        result = await self.db.execute(stmt)
        return result.scalars().all()