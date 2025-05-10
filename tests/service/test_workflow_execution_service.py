import pytest
import pytest_asyncio

from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal

# 导入异步仓库
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
# 导入 Service
from stepflow.service.workflow_execution_service import WorkflowExecutionService

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # 在异步上下文中初始化表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 测试结束后销毁表
    # async with async_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_start_and_get(db_session):
    # 1) 先创建仓库
    repo = WorkflowExecutionRepository(db_session)
    # 2) 再创建 Service
    service = WorkflowExecutionService(repo)

    wf = await service.start_workflow("flow123", shard_id=1, workflow_type="TestType")
    assert wf.run_id is not None

    fetched = await service.get_execution(wf.run_id)
    assert fetched is not None
    assert fetched.status == "running"

@pytest.mark.asyncio
async def test_complete_workflow(db_session):
    repo = WorkflowExecutionRepository(db_session)
    service = WorkflowExecutionService(repo)

    wf_list = await service.list_workflows()
    assert wf_list, "No workflow found, cannot test complete_workflow"
    run_id = wf_list[0].run_id

    ok = await service.complete_workflow(run_id, result='{"success":true}')
    assert ok is True

    updated = await service.get_execution(run_id)
    assert updated.status == "completed"
    assert updated.result is not None

@pytest.mark.asyncio
async def test_delete_workflow(db_session):
    repo = WorkflowExecutionRepository(db_session)
    service = WorkflowExecutionService(repo)

    wf_list = await service.list_workflows()
    assert wf_list, "No workflow found, cannot test delete_workflow"
    run_id = wf_list[0].run_id

    success = await service.delete_workflow(run_id)
    assert success is True

    again = await service.get_execution(run_id)
    assert again is None