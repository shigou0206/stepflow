
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import delete
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal
from stepflow.persistence.models import WorkflowEvent
from stepflow.events.eventbus_model import EventEnvelope, EventType
from stepflow.persistence.sql_event_store import SqlAlchemyEventStore


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    import stepflow.persistence.models  # Ensure model loaded
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # async with async_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as db:
        yield db


@pytest.mark.asyncio
async def test_event_store_isolation(db_session):
    store = SqlAlchemyEventStore(db_session)

    await db_session.execute(delete(WorkflowEvent).where(WorkflowEvent.run_id.in_(["run-x", "run-y"])))
    await db_session.commit()

    event1 = EventEnvelope(
        run_id="run-x",
        shard_id=0,
        event_id=1,
        event_type=EventType.NodeEnter,
        timestamp=datetime.now(timezone.utc),
        state_id="step-x",
        attributes={"a": 1}
    )
    event2 = EventEnvelope(
        run_id="run-y",
        shard_id=0,
        event_id=1,
        event_type=EventType.NodeEnter,
        timestamp=datetime.now(timezone.utc),
        state_id="step-y",
        attributes={"a": 2}
    )

    await store.save_events([event1, event2])

    events_x = await store.load_events("run-x")
    events_y = await store.load_events("run-y")
    assert len(events_x) == 1
    assert len(events_y) == 1
    assert events_x[0].state_id == "step-x"
    assert events_y[0].state_id == "step-y"


@pytest.mark.asyncio
async def test_event_store_unordered_ids(db_session):
    store = SqlAlchemyEventStore(db_session)

    await db_session.execute(delete(WorkflowEvent).where(WorkflowEvent.run_id == "run-unordered"))
    await db_session.commit()

    unordered = [
        EventEnvelope(run_id="run-unordered", shard_id=0, event_id=3, event_type=EventType.NodeEnter,
                      timestamp=datetime.now(timezone.utc), state_id="s3", attributes={}),
        EventEnvelope(run_id="run-unordered", shard_id=0, event_id=1, event_type=EventType.NodeEnter,
                      timestamp=datetime.now(timezone.utc), state_id="s1", attributes={}),
        EventEnvelope(run_id="run-unordered", shard_id=0, event_id=2, event_type=EventType.NodeEnter,
                      timestamp=datetime.now(timezone.utc), state_id="s2", attributes={}),
    ]

    await store.save_events(unordered)

    loaded = await store.load_events("run-unordered")
    assert [e.event_id for e in loaded] == [1, 2, 3]


@pytest.mark.asyncio
async def test_event_store_restore_fields(db_session):
    store = SqlAlchemyEventStore(db_session)

    await db_session.execute(delete(WorkflowEvent).where(WorkflowEvent.run_id == "run-trace"))
    await db_session.commit()

    event = EventEnvelope(
        run_id="run-trace",
        shard_id=0,
        event_id=1,
        event_type=EventType.NodeEnter,
        timestamp=datetime.now(timezone.utc),
        state_id="step",
        state_type="Task",
        trace_id="t-001",
        parent_event_id=0,
        context_version=1,
        attributes={}
    )
    await store.save_event(event)

    result = await store.load_events("run-trace")
    assert result[0].trace_id == "t-001"
    assert result[0].parent_event_id == 0
    assert result[0].state_id == "step"


@pytest.mark.asyncio
async def test_get_last_event_id_empty(db_session):
    store = SqlAlchemyEventStore(db_session)
    last = await store.get_last_event_id("non-existent-run")
    assert last == 0
