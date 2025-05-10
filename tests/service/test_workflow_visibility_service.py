import pytest
import pytest_asyncio

# 导入异步数据库配置
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal

# 导入异步仓库 + Service
from stepflow.persistence.repositories.workflow_visibility_repository import WorkflowVisibilityRepository
from stepflow.service.workflow_visibility_service import WorkflowVisibilityService

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # 在异步上下文里 create_all
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 测试结束后 drop
    # async with async_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_create_and_update_visibility(db_session):
    # 1) 先创建仓库
    repo = WorkflowVisibilityRepository(db_session)
    # 2) 再用仓库创建 Service
    svc = WorkflowVisibilityService(repo)

    await svc.create_visibility(
        run_id="run-xyz",
        workflow_id="wf-456",
        workflow_type="VisibilityTest",
        status="running"
    )
    got = await svc.get_visibility("run-xyz")
    assert got is not None
    assert got.status == "running"

    await svc.update_visibility_status("run-xyz", "completed")
    updated = await svc.get_visibility("run-xyz")
    assert updated is not None
    assert updated.status == "completed"
    assert updated.close_time is not None

@pytest.mark.asyncio
async def test_delete_visibility(db_session):
    repo = WorkflowVisibilityRepository(db_session)
    svc = WorkflowVisibilityService(repo)

    deleted = await svc.delete_visibility("run-xyz")
    assert deleted is True

    again = await svc.get_visibility("run-xyz")
    assert again is None