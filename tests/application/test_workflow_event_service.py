import pytest
import pytest_asyncio
from datetime import datetime

# 使用异步数据库配置
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal

# 导入异步仓库 + Service
from stepflow.infrastructure.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.application.workflow_event_service import WorkflowEventService

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # 在异步上下文里 create_all
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 测试完后 drop_all
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_record_and_archive(db_session):
    # 1) 创建异步仓库
    repo = WorkflowEventRepository(db_session)
    # 2) 创建Service，注入repo
    service = WorkflowEventService(repo)

    evt = await service.record_event(
        run_id="run-xyz",
        shard_id=0,
        event_id=1,
        event_type="TestEvent",
        attributes='{"some":"attr"}'
    )
    assert evt.id is not None
    assert evt.archived is False

    all_evts = await service.list_events_for_run("run-xyz")
    assert len(all_evts) == 1
    assert all_evts[0].event_type == "TestEvent"

    ok = await service.archive_event(evt.id)
    assert ok is True

    archived_evt = await service.get_event(evt.id)
    assert archived_evt.archived is True

@pytest.mark.asyncio
async def test_delete_event(db_session):
    # 同样先创建仓库、再注入Service
    repo = WorkflowEventRepository(db_session)
    service = WorkflowEventService(repo)

    evts = await service.list_events_for_run("run-xyz")
    if not evts:
        return  # 没有可删的事件就直接return，避免空列表

    db_id = evts[0].id
    success = await service.delete_event(db_id)
    assert success is True

    again = await service.get_event(db_id)
    assert again is None