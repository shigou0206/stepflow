import pytest
import pytest_asyncio
from datetime import datetime, timedelta

# 1) 导入异步数据库设置
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal

# 2) 导入 TimerRepository (异步版) 和 TimerService
from stepflow.persistence.repositories.timer_repository import TimerRepository
from stepflow.service.timer_service import TimerService

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    """
    在异步上下文里，使用 async_engine.begin() + run_sync(...) 来创建表。
    测试全部结束后再 drop_all。
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # async with async_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    """
    提供一个 AsyncSession 用于测试。
    """
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_schedule_and_cancel(db_session):
    """
    测试 schedule_timer / cancel_timer
    """
    # 首先创建 TimerRepository，再注入 TimerService
    repo = TimerRepository(db_session)
    service = TimerService(repo)

    now = datetime.now()
    t = await service.schedule_timer(
        run_id="run-abc",
        shard_id=1,
        fire_at=now + timedelta(seconds=60)
    )
    assert t.timer_id is not None
    assert t.status == "scheduled"

    cancel_ok = await service.cancel_timer(t.timer_id)
    assert cancel_ok is True

    again = await service.list_timers_for_run("run-abc")
    assert again[0].status == "canceled"

@pytest.mark.asyncio
async def test_fire_timer(db_session):
    """
    测试 fire_timer
    """
    repo = TimerRepository(db_session)
    service = TimerService(repo)

    t = await service.schedule_timer(
        run_id="run-def",
        shard_id=2,
        fire_at=datetime.now()
    )
    fired_ok = await service.fire_timer(t.timer_id)
    assert fired_ok is True

    updated_list = await service.list_timers_for_run("run-def")
    assert updated_list[0].status == "fired"

@pytest.mark.asyncio
async def test_find_due_timers(db_session):
    """
    测试 list_scheduled_before
    """
    repo = TimerRepository(db_session)
    service = TimerService(repo)

    t = await service.schedule_timer(
        run_id="run-ghi",
        shard_id=3,
        fire_at=datetime.now() - timedelta(seconds=5)
    )
    due = await service.find_due_timers(datetime.now())
    assert any(x.timer_id == t.timer_id for x in due)