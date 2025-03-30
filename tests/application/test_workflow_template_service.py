# tests/application/test_workflow_template_service_async.py

import pytest
import pytest_asyncio

# 使用异步数据库配置
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal

# 导入异步版的仓库 + Service
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.application.workflow_template_service import WorkflowTemplateService

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

    # 调用 Service 方法
    tpl = await service.create_template(
        name="TestFlow",
        dsl_definition='{"Version":"1.0"}',
        description="desc"
    )
    assert tpl.template_id is not None

    fetched = await service.get_template(tpl.template_id)
    assert fetched is not None
    assert fetched.name == "TestFlow"
    assert fetched.description == "desc"

@pytest.mark.asyncio
async def test_update_template(db_session):
    repo = WorkflowTemplateRepository(db_session)
    service = WorkflowTemplateService(repo)

    tpl_list = await service.list_templates()
    assert len(tpl_list) > 0

    tpl_id = tpl_list[0].template_id
    updated = await service.update_template(tpl_id, new_name="UpdatedFlow")
    assert updated is not None
    assert updated.name == "UpdatedFlow"

@pytest.mark.asyncio
async def test_delete_template(db_session):
    repo = WorkflowTemplateRepository(db_session)
    service = WorkflowTemplateService(repo)

    tpl_list = await service.list_templates()
    assert tpl_list, "No template found to delete"

    tpl_id = tpl_list[0].template_id
    is_deleted = await service.delete_template(tpl_id)
    assert is_deleted is True

    not_found = await service.get_template(tpl_id)
    assert not_found is None