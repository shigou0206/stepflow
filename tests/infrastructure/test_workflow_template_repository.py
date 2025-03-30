import pytest
import pytest_asyncio
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowTemplate
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository

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
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_create_and_get_template(db_session):
    repo = WorkflowTemplateRepository(db_session)
    template = WorkflowTemplate(
        template_id="test-id",
        name="Test Template",
        description="A sample description",
        dsl_definition='{"Version":"1.0"}'
    )

    created = await repo.create(template)
    assert created.template_id == "test-id"

    fetched = await repo.get_by_id("test-id")
    assert fetched is not None
    assert fetched.name == "Test Template"

@pytest.mark.asyncio
async def test_update_template(db_session):
    repo = WorkflowTemplateRepository(db_session)
    t = await repo.get_by_id("test-id")
    assert t is not None

    t.name = "Updated Name"
    updated = await repo.update(t)
    assert updated.name == "Updated Name"

@pytest.mark.asyncio
async def test_delete_template(db_session):
    repo = WorkflowTemplateRepository(db_session)
    deleted = await repo.delete("test-id")
    assert deleted is True

    not_found = await repo.get_by_id("test-id")
    assert not_found is None