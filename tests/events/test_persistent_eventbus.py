
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from stepflow.events.eventbus_model import EventEnvelope, EventType
from stepflow.persistence.sql_event_store import SqlAlchemyEventStore
from stepflow.events.persistent_eventbus import PersistentEventBus
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal

import stepflow.persistence.models

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


@pytest.mark.asyncio
async def test_persistent_bus_publish_single(db_session):
    store = SqlAlchemyEventStore(db_session)
    bus = PersistentEventBus(store)

    event = EventEnvelope(
        run_id="test-run-1",
        shard_id=1,
        event_id=100,
        event_type=EventType.NodeEnter,
        timestamp=datetime.now(timezone.utc),
        state_id="Init",
        state_type="Pass",
        attributes={"input": {"msg": "hello"}}
    )

    await bus.publish(event)

    # verify internal log
    log = bus.get_event_log()
    assert len(log) == 1
    assert log[0].event_type == EventType.NodeEnter

    # verify from store
    result = await store.load_events("test-run-1")
    assert len(result) == 1
    assert result[0].attributes["input"]["msg"] == "hello"


@pytest.mark.asyncio
async def test_persistent_bus_batch_publish(db_session):
    store = SqlAlchemyEventStore(db_session)
    bus = PersistentEventBus(store)

    events = []
    for i in range(3):
        events.append(EventEnvelope(
            run_id="batch-run",
            shard_id=0,
            event_id=i+1,
            event_type=EventType.NodeSuccess,
            timestamp=datetime.now(timezone.utc),
            state_id=f"Step{i}",
            state_type="Task",
            attributes={"output": i}
        ))

    await bus.publish_batch(events)

    # verify internal log
    log = bus.get_event_log()
    assert len(log) == 3

    # verify from store
    result = await store.load_events("batch-run")
    assert len(result) == 3
    assert result[2].state_id == "Step2"
    assert result[2].attributes["output"] == 2


@pytest.mark.asyncio
async def test_get_last_event_id(db_session):
    store = SqlAlchemyEventStore(db_session)
    last_id = await store.get_last_event_id("batch-run")
    assert last_id == 3
