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

    async def create_template(self, name: str, dsl_definition: str, description: Optional[str] = None) -> WorkflowTemplate:
        """创建一个新的工作流模板."""
        template = WorkflowTemplate(
            template_id=str(uuid.uuid4()),
            name=name,
            dsl_definition=dsl_definition,
            description=description,
            updated_at=datetime.now()  # 手动赋值, 也可依赖数据库默认值
        )
        return await self.repo.create(template)

    async def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        return await self.repo.get_by_id(template_id)

    async def update_template(self, template_id: str, new_name: Optional[str] = None, new_description: Optional[str] = None) -> Optional[WorkflowTemplate]:
        """更新模板名称或描述."""
        template = await self.repo.get_by_id(template_id)
        if not template:
            return None
        if new_name is not None:
            template.name = new_name
        if new_description is not None:
            template.description = new_description
        template.updated_at = datetime.now()
        return await self.repo.update(template)

    async def delete_template(self, template_id: str) -> bool:
        return await self.repo.delete(template_id)

    async def list_templates(self) -> List[WorkflowTemplate]:
        return await self.repo.list_all()