import pytest
import pytest_asyncio
import json
from datetime import datetime
import pytz

# 用异步 engine / session
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowTemplate, WorkflowExecution, WorkflowEvent
# 你的异步 replay function
from stepflow.domain.engine.replay import replay_workflow

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
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()

@pytest.mark.asyncio
async def test_replay_scenario(db_session):
    # 1) Insert a template & execution
    tpl = WorkflowTemplate(
        template_id="tpl-1",
        name="TestTemplate",
        dsl_definition="""{
           "Version":"1.0",
           "Name":"SimpleFlow",
           "StartAt":"Step1",
           "States":{
             "Step1":{"Type":"Pass","Next":"Step2"},
             "Step2":{"Type":"Succeed"}
           }
        }"""
    )
    db_session.add(tpl)

    wf_exec = WorkflowExecution(
        run_id="run-123",
        workflow_id="wf-123",
        shard_id=1,
        template_id="tpl-1",
        status="running",
        workflow_type="TestFlow",
        # 如果你想用时区感知，可以:
        start_time=datetime.now(pytz.utc),
        # input需字符串
        input=json.dumps({"foo": "bar"})
    )
    db_session.add(wf_exec)
    await db_session.commit()

    # 2) Insert some events
    evt1 = WorkflowEvent(
        run_id="run-123",
        shard_id=1,
        event_id=1,
        event_type="WorkflowExecutionStarted",
        attributes=json.dumps({"input": {"foo": "bar"}}),
    )
    evt2 = WorkflowEvent(
        run_id="run-123",
        shard_id=1,
        event_id=2,
        event_type="TaskStateFinished",
        attributes=json.dumps({"next": "Step2"}),
    )
    evt3 = WorkflowEvent(
        run_id="run-123",
        shard_id=1,
        event_id=3,
        event_type="WorkflowExecutionSucceeded",
        attributes=json.dumps({}),
    )
    db_session.add_all([evt1, evt2, evt3])
    await db_session.commit()

    # 3) call replay (异步)
    ctx, status = await replay_workflow(db_session, "run-123")
    assert status == "completed"
    print("Replay context:", ctx, " status:", status)