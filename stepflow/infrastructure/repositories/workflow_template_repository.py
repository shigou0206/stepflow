# stepflow/infrastructure/repositories/workflow_template_repository.py

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from stepflow.infrastructure.models import WorkflowTemplate

class WorkflowTemplateRepository:
    def __init__(self, db: AsyncSession):
        """
        db: 一般来自于 dependency (e.g. FastAPI's Depends(get_db_session))
        或在脚本中手动创建异步session.
        """
        self.db = db

    async def create(self, template: WorkflowTemplate) -> WorkflowTemplate:
        """
        将一个新的 WorkflowTemplate 对象插入到数据库.
        你可以先在外部构造好 template 实例, 再调用此方法.
        """
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_by_id(self, template_id: str) -> Optional[WorkflowTemplate]:
        """
        根据 template_id 获取记录, 若不存在则返回 None
        """
        stmt = select(WorkflowTemplate).where(WorkflowTemplate.template_id == template_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, template: WorkflowTemplate) -> WorkflowTemplate:
        """
        更新一个已存在的 template 对象 (要求你先在 session 内查询到),
        然后执行 commit 刷新.
        """
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def delete(self, template_id: str) -> bool:
        """
        根据 template_id 删除对应记录, 返回是否删除成功.
        """
        obj = await self.get_by_id(template_id)
        if obj is None:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True

    async def list_all(self) -> List[WorkflowTemplate]:
        """
        获取所有模板 (小项目可直接全表扫描, 大项目需分页)
        """
        stmt = select(WorkflowTemplate)
        result = await self.db.execute(stmt)
        return result.scalars().all()