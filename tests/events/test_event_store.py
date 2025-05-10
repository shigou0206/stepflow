
import pytest
import pytest_asyncio
import json
from datetime import datetime, timezone
import stepflow.persistence.models

from sqlalchemy.ext.asyncio import AsyncSession
from stepflow.persistence.database import Base, async_engine, AsyncSessionLocal
from stepflow.events.eventbus_model import EventEnvelope, EventType
from stepflow.persistence.sql_event_store import SqlAlchemyEventStore


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
async def test_save_and_load_event(db_session: AsyncSession):
    store = SqlAlchemyEventStore(db_session)
    event = EventEnvelope(
        run_id="run-test-1",
        shard_id=0,
        event_id=1,
        event_type=EventType.NodeSuccess,
        timestamp=datetime.now(timezone.utc),
        state_id="step-1",
        state_type="Task",
        attributes={"output": {"value": 123}}
    )

    await store.save_event(event)

    events = await store.load_events(run_id="run-test-1")
    assert len(events) == 1
    assert events[0].event_type == EventType.NodeSuccess
    assert events[0].attributes["output"]["value"] == 123


@pytest.mark.asyncio
async def test_get_last_event_id(db_session: AsyncSession):
    store = SqlAlchemyEventStore(db_session)
    last_id = await store.get_last_event_id("run-test-1")
    assert last_id == 1
