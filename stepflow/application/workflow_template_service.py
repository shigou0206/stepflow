# stepflow/application/workflow_template_service.py

import uuid
from datetime import datetime
from typing import Optional, List
from stepflow.infrastructure.models import WorkflowTemplate
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository

class WorkflowTemplateService:
    def __init__(self, repo: WorkflowTemplateRepository):
        # 注入一个异步版本的 WorkflowTemplateRepository
        self.repo = repo

    async def create_template(self, template: WorkflowTemplate) -> WorkflowTemplate:
        """
        创建新的工作流模板
        """
        return await self.repo.create(template)

    async def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """
        获取工作流模板
        """
        return await self.repo.get_by_id(template_id)

    async def update_template(self, template: WorkflowTemplate) -> WorkflowTemplate:
        """
        更新工作流模板
        """
        return await self.repo.update(template)

    async def delete_template(self, template_id: str) -> bool:
        """
        删除工作流模板
        """
        return await self.repo.delete(template_id)

    async def list_templates(self) -> List[WorkflowTemplate]:
        """
        列出所有工作流模板
        """
        return await self.repo.list_all()