# stepflow/application/workflow_visibility_service.py

from typing import Optional, List
from datetime import datetime
from stepflow.infrastructure.models import WorkflowVisibility
from stepflow.infrastructure.repositories.workflow_visibility_repository import WorkflowVisibilityRepository

class WorkflowVisibilityService:
    def __init__(self, repo: WorkflowVisibilityRepository):
        self.repo = repo

    async def create_visibility(
        self,
        run_id: str,
        workflow_id: str,
        workflow_type: str,
        status: str,
        memo: str = None,
        search_attrs: str = None
    ) -> WorkflowVisibility:
        """
        创建一条可见性记录
        """
        vis = WorkflowVisibility(
            run_id=run_id,
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            status=status,
            start_time=datetime.now(),
            memo=memo,
            search_attrs=search_attrs
        )
        return await self.repo.create(vis)

    async def get_visibility(self, run_id: str) -> Optional[WorkflowVisibility]:
        return await self.repo.get_by_run_id(run_id)

    async def update_visibility_status(self, run_id: str, new_status: str) -> bool:
        """
        更新可见性记录的状态, 若状态为 completed/failed 等可补充 close_time
        """
        obj = await self.repo.get_by_run_id(run_id)
        if not obj:
            return False
        obj.status = new_status
        if new_status in ("completed", "failed", "canceled"):
            obj.close_time = datetime.now()
        await self.repo.update(obj)
        return True

    async def delete_visibility(self, run_id: str) -> bool:
        return await self.repo.delete(run_id)

    async def list_vis_by_status(self, status: str) -> List[WorkflowVisibility]:
        return await self.repo.list_by_status(status)