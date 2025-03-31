# stepflow/interfaces/api/workflow_template_endpoints.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from stepflow.infrastructure.database import get_db_session
from stepflow.application.workflow_template_service import WorkflowTemplateService
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository
router = APIRouter(prefix="/templates", tags=["workflow_templates"])

class CreateTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    dsl_definition: str

@router.post("/")
async def create_template(req: CreateTemplateRequest, db=Depends(get_db_session)):
    repo = WorkflowTemplateRepository(db)
    service = WorkflowTemplateService(repo)
    tpl = await service.create_template(
        name=req.name,
        description=req.description,
        dsl_definition=req.dsl_definition
    )
    return {"template_id": tpl.template_id, "name": tpl.name}

@router.get("/{template_id}")
async def get_template(template_id: str, db=Depends(get_db_session)):
    repo = WorkflowTemplateRepository(db)
    service = WorkflowTemplateService(repo)
    tpl = await service.get_template(template_id)
    if not tpl:
        return {"error": "Not found"}
    return {
        "template_id": tpl.template_id,
        "name": tpl.name,
        "description": tpl.description,
        "dsl": tpl.dsl_definition
    }