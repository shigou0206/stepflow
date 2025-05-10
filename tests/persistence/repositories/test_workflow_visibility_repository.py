import pytest
import pytest_asyncio
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal
from stepflow.persistence.models import WorkflowVisibility
from stepflow.persistence.repositories.workflow_visibility_repository import WorkflowVisibilityRepository

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # 在异步上下文里创建表
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
async def test_create_and_get_visibility(db_session):
    repo = WorkflowVisibilityRepository(db_session)
    vis = WorkflowVisibility(
        run_id="run-1",
        workflow_id="wf-123",
        workflow_type="TestFlow",
        status="running"
    )
    created = await repo.create(vis)
    assert created.run_id == "run-1"

    fetched = await repo.get_by_run_id("run-1")
    assert fetched is not None
    assert fetched.status == "running"

@pytest.mark.asyncio
async def test_delete_visibility(db_session):
    repo = WorkflowVisibilityRepository(db_session)
    deleted = await repo.delete("run-1")
    assert deleted is True

    again = await repo.get_by_run_id("run-1")
    assert again is None