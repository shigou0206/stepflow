import pytest
import pytest_asyncio
import json
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import select

from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.models import (
    WorkflowTemplate,
    WorkflowExecution,
    WorkflowEvent,
    ActivityTask
)
from stepflow.domain.engine.execution_engine import advance_workflow

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    """
    在异步上下文里创建/销毁数据库表
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    """
    提供异步 Session
    """
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()

@pytest.mark.asyncio
async def test_task_state_execution(db_session):
    """
    测试一个简单的 DSL: 
      StartAt: Step1
      Step1: TaskState(ActivityType='myActivity'), End=True
    验证:
      1) 首次 advance_workflow => 创建 ActivityTask, 记录事件
      2) 更新 ActivityTask => completed
      3) 二次 advance_workflow => 状态变 completed
    """

    # 1) 插入 Template(DSL)
    tpl_id = "tpl-1"
    dsl_definition = json.dumps({
        "Version": "1.0",
        "Name": "SimpleFlow",
        "StartAt": "Step1",
        "States": {
            "Step1": {
                "Type": "Task",
                "ActivityType": "myActivity",
                "End": True
            }
        }
    })

    tpl = WorkflowTemplate(
        template_id=tpl_id,
        name="TestTemplate",
        dsl_definition=dsl_definition
    )
    db_session.add(tpl)

    # 2) 插入 WorkflowExecution
    run_id = "run-123"
    wf_exec = WorkflowExecution(
        run_id=run_id,
        workflow_id="wf-123",
        shard_id=1,
        template_id=tpl_id,
        status="running",
        workflow_type="TestFlow",
        start_time=datetime.now(UTC)
    )
    db_session.add(wf_exec)
    await db_session.commit()

    # 第一次 advance => 预期创建 ActivityTask, 事件= ActivityTaskScheduled
    await advance_workflow(db_session, run_id)

    # 检查 ActivityTask
    # 替换 db_session.query(ActivityTask) => select(ActivityTask)
    at_stmt = select(ActivityTask).where(ActivityTask.run_id == run_id)
    at_result = await db_session.execute(at_stmt)
    act = at_result.scalars().one_or_none()

    assert act is not None, "Expected ActivityTask created"
    assert act.status == "scheduled"

    # 检查 事件
    evt_stmt = select(WorkflowEvent).where(WorkflowEvent.run_id == run_id)
    evt_result = await db_session.execute(evt_stmt)
    events = evt_result.scalars().all()
    # 应至少有 ActivityTaskScheduled 事件
    assert any(e.event_type == "ActivityTaskScheduled" for e in events)

    # 模拟外部worker回调 => ActivityTask完成
    act.status = "completed"
    act.result = json.dumps({"some": "result"})
    await db_session.commit()

    # 第二次 advance => 预期 TaskState 执行完 => workflow_executions.status=completed
    await advance_workflow(db_session, run_id)

    # 再查 workflow
    wf_stmt2 = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
    wf_q2 = await db_session.execute(wf_stmt2)
    updated_wf = wf_q2.scalars().one()
    assert updated_wf.status == "completed"
    assert updated_wf.close_time is not None

    # 检查事件 => 有 "WorkflowExecutionCompleted"
    evt_stmt2 = select(WorkflowEvent).where(WorkflowEvent.run_id == run_id)
    evt_q2 = await db_session.execute(evt_stmt2)
    all_events = evt_q2.scalars().all()
    assert any(e.event_type == "WorkflowExecutionCompleted" for e in all_events)

@pytest.mark.asyncio
async def test_choice_state_execution(db_session):
    """
    如需要测试 ChoiceState, 也可以插入对应 DSL
    ...
    """
    pass

@pytest.mark.asyncio
async def test_pass_state_end(db_session):
    """
    测试 PassState 的执行
    ...
    """
    pass