from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from stepflow.persistence.database import get_db_session
from stepflow.service.workflow_template_service import WorkflowTemplateService
from stepflow.persistence.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.persistence.models import WorkflowTemplate
from stepflow.interfaces.api.schemas import (
    WorkflowTemplateCreate,
    WorkflowTemplateResponse,
    WorkflowTemplateUpdate
)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/workflow_templates", tags=["workflow_templates"])

# ----------- 通用返回封装 -----------

def standard_response(
    status: str = "ok",
    data: Optional[Any] = None,
    message: Optional[str] = None
) -> Dict[str, Any]:
    return {"status": status, "data": data, "message": message}

# ----------- 接口定义 -----------

@router.get("/", response_model=Dict[str, Any])
async def list_templates(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    repo = WorkflowTemplateRepository(db)
    templates = await repo.list_all()
    items = templates[skip: skip + limit]
    return standard_response(data=[WorkflowTemplateResponse.model_validate(t) for t in items])


@router.post("/", response_model=Dict[str, Any])
async def create_template(
    template: WorkflowTemplateCreate,
    db: AsyncSession = Depends(get_db_session)
):
    repo = WorkflowTemplateRepository(db)
    service = WorkflowTemplateService(repo)

    template_id = template.template_id or str(uuid.uuid4())

    existing = await repo.get_by_id(template_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Template with ID {template_id} already exists")

    new_template = WorkflowTemplate(
        template_id=template_id,
        name=template.name,
        description=template.description,
        dsl_definition=template.dsl_definition,
        updated_at=datetime.now()
    )

    created = await service.create_template(new_template)
    return standard_response(data=WorkflowTemplateResponse.model_validate(created), message="Template created")


@router.get("/{template_id}", response_model=Dict[str, Any])
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    repo = WorkflowTemplateRepository(db)
    tmpl = await repo.get_by_id(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return standard_response(data=WorkflowTemplateResponse.model_validate(tmpl))


@router.put("/{template_id}", response_model=Dict[str, Any])
async def update_template(
    template_id: str,
    template_update: WorkflowTemplateUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    repo = WorkflowTemplateRepository(db)
    service = WorkflowTemplateService(repo)

    existing = await repo.get_by_id(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")

    # 更新字段
    if template_update.name is not None:
        existing.name = template_update.name
    if template_update.description is not None:
        existing.description = template_update.description
    if template_update.dsl_definition is not None:
        existing.dsl_definition = template_update.dsl_definition
    existing.updated_at = datetime.now()

    updated = await service.update_template(existing)
    return standard_response(data=WorkflowTemplateResponse.model_validate(updated), message="Template updated")


@router.delete("/{template_id}", response_model=Dict[str, Any])
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    repo = WorkflowTemplateRepository(db)
    service = WorkflowTemplateService(repo)

    success = await service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

    return standard_response(message=f"Template {template_id} deleted")