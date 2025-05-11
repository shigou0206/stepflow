import pytest
import json
import pytest_asyncio
from stepflow.persistence.database import async_engine, Base
from stepflow.hooks.db_hook import DBHook
from stepflow.service.workflow_event_service import WorkflowEventService
from stepflow.service.workflow_execution_service import WorkflowExecutionService
from stepflow.service.workflow_visibility_service import WorkflowVisibilityService
from stepflow.persistence.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.persistence.repositories.workflow_visibility_repository import WorkflowVisibilityRepository
from stepflow.persistence.models import WorkflowExecution, WorkflowVisibility
from stepflow.persistence.database import AsyncSessionLocal
from datetime import datetime, UTC

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_db_hook_end_to_end():
    run_id = "hook-run-001"
    state_id = "TestState"
    context = {"input": 123}
    output = {"result": "ok"}
    reason = "testing cancel"

    async with AsyncSessionLocal() as session:
        # 预置执行记录和可见性记录
        exec_repo = WorkflowExecutionRepository(session)
        vis_repo = WorkflowVisibilityRepository(session)

        exec_ = WorkflowExecution(
            run_id=run_id,
            workflow_id="wf-1",
            template_id="tmpl-1",
            shard_id=1,
            status="running",
            mode="inline",
            workflow_type="Demo",
            input=json.dumps(context),
            start_time=datetime.now(UTC)
        )
        vis = WorkflowVisibility(
            run_id=run_id,
            workflow_id="wf-1",
            workflow_type="Demo",
            status="running",
            start_time=datetime.now(UTC)
        )
        await exec_repo.create(exec_)
        await vis_repo.create(vis)

        # 构建 Hook 依赖
        hook = DBHook(
            execution_service=WorkflowExecutionService(exec_repo),
            event_service=WorkflowEventService(WorkflowEventRepository(session)),
            visibility_service=WorkflowVisibilityService(vis_repo),
            shard_id=1
        )

        # 执行 Hook 各方法
        await hook.on_workflow_start(run_id)
        await hook.on_node_enter(run_id, state_id, context)
        await hook.on_node_success(run_id, state_id, output)
        await hook.on_node_fail(run_id, state_id, "oops")
        await hook.on_node_dispatch(run_id, state_id, context)
        await hook.on_control_signal(run_id, "Cancel", reason)
        await hook.on_workflow_end(run_id, output)

        await session.commit()

        # 校验事件总数
        event_repo = WorkflowEventRepository(session)
        events = await event_repo.list_by_run_id(run_id)
        types = [e.event_type for e in events]
        assert "WorkflowStart" in types
        assert "NodeEnter" in types
        assert "NodeSuccess" in types
        assert "NodeFail" in types
        assert "NodeDispatch" in types
        assert "WorkflowControl" in types
        assert "WorkflowEnd" in types
        assert len(events) == 7

        # 校验状态变更
        exec_fresh = await exec_repo.get_by_run_id(run_id)
        vis_fresh = await vis_repo.get_by_run_id(run_id)
        assert exec_fresh.status == "canceled"  # 因为 control_signal 是 Cancel
        assert vis_fresh.status == "canceled"