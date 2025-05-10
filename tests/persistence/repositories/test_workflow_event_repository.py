import pytest
import pytest_asyncio
import uuid
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal
from stepflow.persistence.models import WorkflowEvent
from stepflow.persistence.repositories.workflow_event_repository import WorkflowEventRepository

@pytest_asyncio.fixture(scope="module", autouse=True)
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
async def test_create_and_list_by_run_id(db_session):
    repo = WorkflowEventRepository(db_session)

    evt1 = WorkflowEvent(
        run_id="run-1",
        shard_id=0,
        event_id=1,
        event_type="Started",
        attributes='{"foo":"bar"}'
    )
    created1 = await repo.create(evt1)
    assert created1.id is not None

    evt2 = WorkflowEvent(
        run_id="run-1",
        shard_id=0,
        event_id=2,
        event_type="SomethingHappened"
    )
    created2 = await repo.create(evt2)
    assert created2.id is not None

    # list_by_run_id
    events = await repo.list_by_run_id("run-1")
    assert len(events) == 2
    assert events[0].event_id == 1
    assert events[1].event_id == 2

@pytest.mark.asyncio
async def test_delete_event(db_session):
    repo = WorkflowEventRepository(db_session)
    events = await repo.list_by_run_id("run-1")
    evt_id_pk = events[0].id  # 取第一条记录

    deleted = await repo.delete(evt_id_pk)
    assert deleted is True

    again = await repo.get_by_id(evt_id_pk)
    assert again is None

@pytest.mark.asyncio
async def test_archived_field(db_session):
    repo = WorkflowEventRepository(db_session)
    remaining_events = await repo.list_by_run_id("run-1")
    if remaining_events:
        e = remaining_events[0]
        e.archived = True
        updated = await repo.update(e)
        assert updated.archived is True