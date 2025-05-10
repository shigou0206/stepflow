from typing import Optional, List, Dict
from stepflow.persistence.models import WorkflowTemplate
from stepflow.persistence.repositories.workflow_template_repository import WorkflowTemplateRepository


class WorkflowTemplateService:
    def __init__(self, repo: WorkflowTemplateRepository):
        self.repo = repo

    async def create_template(self, data: Dict) -> WorkflowTemplate:
        """
        创建新的工作流模板（支持 dict 入参）
        """
        template = WorkflowTemplate(**data)
        return await self.repo.create(template)

    async def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        return await self.repo.get_by_id(template_id)

    async def update_template(self, template: WorkflowTemplate) -> WorkflowTemplate:
        return await self.repo.update(template)

    async def delete_template(self, template_id: str) -> bool:
        return await self.repo.delete(template_id)

    async def list_templates(self, limit: Optional[int] = None, offset: int = 0) -> List[WorkflowTemplate]:
        # 目前 list_all 无分页，可以将分页功能向 repository 下沉
        return await self.repo.list_all()