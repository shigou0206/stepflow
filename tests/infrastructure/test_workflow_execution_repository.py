import pytest
import pytest_asyncio
import uuid

# 改为异步 imports
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowExecution
from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # 在异步上下文里 create_all
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 测试结束后 drop
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    # 提供一个异步 Session
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_create_and_get_workflow(db_session):
    repo = WorkflowExecutionRepository(db_session)
    run_id = str(uuid.uuid4())

    wf_exec = WorkflowExecution(
        run_id=run_id,
        workflow_id="test_flow",
        shard_id=0,
        status="running",
        workflow_type="TestType"
    )
    created = await repo.create(wf_exec)
    assert created.run_id == run_id

    fetched = await repo.get_by_run_id(run_id)
    assert fetched is not None
    assert fetched.status == "running"

@pytest.mark.asyncio
async def test_update_workflow(db_session):
    repo = WorkflowExecutionRepository(db_session)

    wf_list = await repo.list_all()
    assert wf_list, "No workflow found to update"

    wf = wf_list[0]
    wf.status = "completed"
    updated = await repo.update(wf)
    assert updated.status == "completed"

@pytest.mark.asyncio
async def test_delete_workflow(db_session):
    repo = WorkflowExecutionRepository(db_session)

    wf_list = await repo.list_all()
    assert wf_list, "No workflow found to delete"
    run_id = wf_list[0].run_id

    deleted = await repo.delete(run_id)
    assert deleted is True

    again = await repo.get_by_run_id(run_id)
    assert again is None