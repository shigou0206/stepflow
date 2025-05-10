import pytest
import pytest_asyncio
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal
from stepflow.persistence.models import ActivityTask
from stepflow.persistence.repositories.activity_task_repository import ActivityTaskRepository

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # 在异步上下文里创建表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 测试完成后 drop
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_create_and_get(db_session):
    repo = ActivityTaskRepository(db_session)
    task = ActivityTask(
        task_token="token-1",
        run_id="run-123",
        shard_id=0,
        seq=1,
        activity_type="test_activity",
        status="scheduled"
    )
    created = await repo.create(task)
    assert created.task_token == "token-1"

    fetched = await repo.get_by_task_token("token-1")
    assert fetched is not None
    assert fetched.status == "scheduled"

@pytest.mark.asyncio
async def test_delete_task(db_session):
    repo = ActivityTaskRepository(db_session)
    deleted = await repo.delete("token-1")
    assert deleted is True

    again = await repo.get_by_task_token("token-1")
    assert again is None