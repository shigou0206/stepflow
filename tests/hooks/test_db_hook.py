import pytest
import json
import pytest_asyncio
from datetime import datetime, UTC

from stepflow.persistence.database import async_engine, Base, AsyncSessionLocal
from stepflow.hooks.db_hook import DBHook
from stepflow.service.workflow_event_service import WorkflowEventService
from stepflow.service.workflow_execution_service import WorkflowExecutionService
from stepflow.service.workflow_visibility_service import WorkflowVisibilityService
from stepflow.persistence.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.persistence.repositories.workflow_visibility_repository import WorkflowVisibilityRepository
from stepflow.persistence.models import WorkflowExecution, WorkflowVisibility


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 清理（可选）：
    # async with async_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as db:
        yield db


@pytest.mark.asyncio
async def test_db_hook_end_to_end(db_session):
    run_id = "hook-run-001"
    state_id = "TestState"
    context = {"input": 123}
    output = {"result": "ok"}
    cancel_reason = "testing cancel"

    exec_repo = WorkflowExecutionRepository(db_session)
    vis_repo = WorkflowVisibilityRepository(db_session)
    event_repo = WorkflowEventRepository(db_session)

    # 准备执行记录
    await exec_repo.create(WorkflowExecution(
        run_id=run_id,
        workflow_id="wf-1",
        template_id="tmpl-1",
        shard_id=1,
        mode="inline",
        status="running",
        workflow_type="Demo",
        input=json.dumps(context),
        start_time=datetime.now(UTC),
        version=1
    ))

    await vis_repo.create(WorkflowVisibility(
        run_id=run_id,
        workflow_id="wf-1",
        workflow_type="Demo",
        status="running",
        start_time=datetime.now(UTC)
    ))

    hook = DBHook(
        execution_service=WorkflowExecutionService(exec_repo),
        event_service=WorkflowEventService(event_repo),
        visibility_service=WorkflowVisibilityService(vis_repo),
        shard_id=1
    )

    # 模拟执行过程
    await hook.on_workflow_start(run_id)
    await hook.on_node_enter(run_id, state_id, context)
    await hook.on_node_success(run_id, state_id, output)
    await hook.on_node_fail(run_id, state_id, "fail-msg")
    await hook.on_node_dispatch(run_id, state_id, context)

    # 模拟取消（状态应变为 canceled）
    await hook.on_control_signal(run_id, "Cancel", cancel_reason)

    # 模拟完成（按逻辑调用顺序，此时应为已取消，不应覆盖状态）
    await hook.on_workflow_end(run_id, output)

    # ⬇️ 校验所有事件记录
    events = await event_repo.list_by_run_id(run_id)
    event_types = [e.event_type for e in events]
    assert len(events) == 7
    assert set(event_types) == {
        "WorkflowStart", "NodeEnter", "NodeSuccess",
        "NodeFail", "NodeDispatch", "WorkflowControl", "WorkflowEnd"
    }

    # ⬇️ 校验事件 ID 递增
    event_ids = [e.event_id for e in events]
    assert event_ids == sorted(event_ids), "event_id 未递增"

    # ⬇️ 校验最终状态为 canceled（不是 completed）
    exec_obj = await exec_repo.get_by_run_id(run_id)
    vis_obj = await vis_repo.get_by_run_id(run_id)

    assert exec_obj.status == "canceled"
    assert vis_obj.status == "canceled"