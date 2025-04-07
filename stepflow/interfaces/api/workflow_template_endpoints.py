# stepflow/interfaces/api/workflow_template_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime
from stepflow.infrastructure.database import get_db_session
from stepflow.application.workflow_template_service import WorkflowTemplateService
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.interfaces.api.schemas import (
    WorkflowTemplateCreate, 
    WorkflowTemplateResponse,
    WorkflowTemplateUpdate
)
from stepflow.infrastructure.models import WorkflowTemplate

router = APIRouter(
    prefix="/workflow_templates",
    tags=["workflow_templates"],
)

class CreateTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    dsl_definition: str

class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dsl_definition: Optional[str] = None

class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None
    dsl: str
    
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=List[WorkflowTemplateResponse])
async def list_templates(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取工作流模板列表
    """
    repo = WorkflowTemplateRepository(db)
    templates = await repo.list_all()
    return templates[skip : skip + limit]

@router.post("/", response_model=WorkflowTemplateResponse)
async def create_template(
    template: WorkflowTemplateCreate, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    创建新的工作流模板
    """
    repo = WorkflowTemplateRepository(db)
    service = WorkflowTemplateService(repo)
    
    # 如果提供了template_id，则使用它，否则生成一个新的
    template_id = template.template_id if hasattr(template, 'template_id') and template.template_id else str(uuid.uuid4())
    
    # 检查是否已存在
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
    return created

@router.get("/{template_id}", response_model=WorkflowTemplateResponse)
async def get_template(
    template_id: str, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取特定工作流模板
    """
    repo = WorkflowTemplateRepository(db)
    template = await repo.get_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/{template_id}", response_model=WorkflowTemplateResponse)
async def update_template(
    template_id: str, 
    template_update: WorkflowTemplateUpdate, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    更新工作流模板
    """
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
    return updated

@router.delete("/{template_id}")
async def delete_template(
    template_id: str, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    删除工作流模板
    """
    repo = WorkflowTemplateRepository(db)
    service = WorkflowTemplateService(repo)
    
    success = await service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"status": "success", "message": f"Template {template_id} deleted"}