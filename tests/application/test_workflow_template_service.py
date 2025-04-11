# tests/application/test_workflow_template_service_async.py

import pytest
import pytest_asyncio
import uuid
from datetime import datetime, UTC

# 使用异步数据库配置
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal

# 导入异步版的仓库 + Service
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.application.workflow_template_service import WorkflowTemplateService
from stepflow.infrastructure.models import WorkflowTemplate

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # 在异步上下文里 create_all
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 测试结束后 drop_all
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    # 提供一个异步 Session
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_create_and_get(db_session):
    # 1) 创建仓库
    repo = WorkflowTemplateRepository(db_session)
    # 2) 创建 Service
    service = WorkflowTemplateService(repo)
    
    # 生成唯一模板ID
    template_id = f"test-template-{uuid.uuid4()}"
    
    # 创建 WorkflowTemplate 对象
    template = WorkflowTemplate(
        template_id=template_id,
        name="TestFlow",
        dsl_definition='{"Version":"1.0"}',
        description="desc"
    )
    
    # 调用 Service 方法
    tpl = await service.create_template(template)
    
    # 验证创建结果
    assert tpl.template_id == template_id
    
    # 获取模板
    retrieved = await service.get_template(template_id)
    assert retrieved is not None
    assert retrieved.template_id == template_id

@pytest.mark.asyncio
async def test_update_template(db_session):
    repo = WorkflowTemplateRepository(db_session)
    service = WorkflowTemplateService(repo)
    
    # 先创建一个模板
    template_id = f"test-update-{uuid.uuid4()}"
    template = WorkflowTemplate(
        template_id=template_id,
        name="UpdateTest",
        dsl_definition='{"Version":"1.0"}',
        description="Original description"
    )
    
    # 创建模板
    tpl = await service.create_template(template)
    
    # 获取模板并修改
    updated_template = await service.get_template(template_id)
    updated_template.dsl_definition = '{"Version":"1.1"}'
    updated_template.description = "Updated description"
    
    # 更新模板
    updated = await service.update_template(updated_template)
    
    # 验证更新结果
    assert updated.template_id == template_id
    assert updated.dsl_definition == '{"Version":"1.1"}'
    assert updated.description == "Updated description"

@pytest.mark.asyncio
async def test_delete_template(db_session):
    repo = WorkflowTemplateRepository(db_session)
    service = WorkflowTemplateService(repo)
    
    # 先创建一个模板
    template_id = f"test-delete-{uuid.uuid4()}"
    template = WorkflowTemplate(
        template_id=template_id,
        name="DeleteTest",
        dsl_definition='{"Version":"1.0"}',
        description="To be deleted"
    )
    
    # 创建模板
    tpl = await service.create_template(template)
    
    # 删除模板
    result = await service.delete_template(template_id)
    assert result is True
    
    # 验证模板已删除
    deleted = await service.get_template(template_id)
    assert deleted is None