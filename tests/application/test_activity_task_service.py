import pytest
import pytest_asyncio
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.application.activity_task_service import ActivityTaskService

@pytest_asyncio.fixture(scope="module")
async def setup_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_schedule_and_start(db_session):
    # 1) 创建仓库
    repo = ActivityTaskRepository(db_session)
    # 2) 创建Service, 注入仓库
    svc = ActivityTaskService(repo)

    # 3) 调用Service的异步方法
    task = await svc.schedule_task(
        run_id="run-xyz",
        shard_id=1,
        seq=1,
        activity_type="test_type",
        input_data="{}"
    )
    assert task.task_token is not None
    assert task.status == "scheduled"

    ok = await svc.start_task(task.task_token)
    assert ok is True

    tasks = await svc.list_tasks_for_run("run-xyz")
    assert tasks[0].status == "running"

@pytest.mark.asyncio
async def test_complete_task(db_session):
    repo = ActivityTaskRepository(db_session)
    svc = ActivityTaskService(repo)

    tasks = await svc.list_tasks_for_run("run-xyz")
    if tasks:
        token = tasks[0].task_token
        ok = await svc.complete_task(token, result_data='{"done":true}')
        assert ok is True

        again = await svc.list_tasks_for_run("run-xyz")
        assert again[0].status == "completed"

@pytest.mark.asyncio
async def test_fail_task(db_session):
    repo = ActivityTaskRepository(db_session)
    svc = ActivityTaskService(repo)

    task = await svc.schedule_task(
        run_id="run-zzz",
        shard_id=2,
        seq=2,
        activity_type="failing_activity",
        input_data="{}"
    )
    ok_fail = await svc.fail_task(task.task_token, result_data='{"error":"something went wrong"}')
    assert ok_fail is True

    again = await svc.list_tasks_for_run("run-zzz")
    assert again[0].status == "failed"