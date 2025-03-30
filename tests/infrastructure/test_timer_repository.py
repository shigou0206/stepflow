import pytest
import pytest_asyncio
from datetime import datetime, timedelta

# 改用异步engine/Session
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.models import Timer
from stepflow.infrastructure.repositories.timer_repository import TimerRepository

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
async def test_create_and_get_timer(db_session):
    repo = TimerRepository(db_session)
    t = Timer(
        timer_id="timer-1",
        run_id="run-1",
        shard_id=0,
        fire_at=datetime.now() + timedelta(seconds=30),
        status="scheduled",
    )
    created = await repo.create(t)
    assert created.timer_id == "timer-1"

    fetched = await repo.get_by_id("timer-1")
    assert fetched is not None
    assert fetched.status == "scheduled"

@pytest.mark.asyncio
async def test_delete_timer(db_session):
    repo = TimerRepository(db_session)
    deleted = await repo.delete("timer-1")
    assert deleted is True

    again = await repo.get_by_id("timer-1")
    assert again is None

@pytest.mark.asyncio
async def test_list_scheduled_before(db_session):
    repo = TimerRepository(db_session)

    # Insert a couple of timers
    t1 = Timer(
        timer_id="timer-2",
        run_id="run-xyz",
        shard_id=1,
        fire_at=datetime.now() - timedelta(seconds=10),  # already due
        status="scheduled"
    )
    await repo.create(t1)

    t2 = Timer(
        timer_id="timer-3",
        run_id="run-xyz",
        shard_id=1,
        fire_at=datetime.now() + timedelta(seconds=300),
        status="scheduled"
    )
    await repo.create(t2)

    # find due timers
    due_list = await repo.list_scheduled_before(datetime.now())
    assert len(due_list) == 1
    assert due_list[0].timer_id == "timer-2"