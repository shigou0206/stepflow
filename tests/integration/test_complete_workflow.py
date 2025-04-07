import pytest
import pytest_asyncio
import json
from datetime import datetime, UTC
import asyncio

from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.models import (
    WorkflowTemplate, 
    WorkflowExecution, 
    WorkflowEvent,
    ActivityTask
)
from stepflow.domain.engine.execution_engine import advance_workflow
from stepflow.application.workflow_execution_service import WorkflowExecutionService
from stepflow.application.activity_task_service import ActivityTaskService
from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    # Create tables in async context
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop tables after tests
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()

@pytest.mark.asyncio
async def test_complete_workflow_execution(db_session):
    """
    Test a complete workflow execution with multiple states and activity tasks
    """
    # 1. Create a workflow template with multiple states
    template = WorkflowTemplate(
        template_id="test-template-1",
        name="Test Workflow",
        dsl_definition=json.dumps({
            "Version": "1.0",
            "Name": "TestWorkflow",
            "StartAt": "TaskA",
            "States": {
                "TaskA": {
                    "Type": "Task",
                    "ActivityType": "ProcessData",
                    "Next": "WaitState"
                },
                "WaitState": {
                    "Type": "Wait",
                    "Seconds": 1,
                    "Next": "TaskB"
                },
                "TaskB": {
                    "Type": "Task",
                    "ActivityType": "FinalizeData",
                    "End": True
                }
            }
        })
    )
    db_session.add(template)
    await db_session.commit()
    
    # 2. Start a workflow execution
    wf_exec_repo = WorkflowExecutionRepository(db_session)
    wf_exec_service = WorkflowExecutionService(wf_exec_repo)
    
    run_id = await wf_exec_service.start_workflow(
        workflow_id="test-workflow-1",
        template_id="test-template-1",
        input_data=json.dumps({"data": "initial value"})
    )
    
    # 3. Verify workflow started correctly
    execution = await wf_exec_repo.get_by_run_id(run_id)
    assert execution.status == "running"
    assert execution.current_state_name == "TaskA"
    
    # 4. Advance workflow to create first activity task
    await advance_workflow(db_session, run_id)
    
    # 5. Find and complete the first activity task
    activity_repo = ActivityTaskRepository(db_session)
    activity_service = ActivityTaskService(activity_repo)
    
    tasks = await activity_repo.list_by_run_id(run_id)
    assert len(tasks) == 1
    assert tasks[0].activity_type == "ProcessData"
    assert tasks[0].status == "scheduled"
    
    # Start the task
    await activity_service.start_task(tasks[0].task_token)
    
    # Complete the task with result
    await activity_service.complete_task(
        tasks[0].task_token, 
        json.dumps({"processed": "data value"})
    )
    
    # 6. Advance workflow again to move to wait state
    await advance_workflow(db_session, run_id)
    
    # Check if we're in the wait state
    execution = await wf_exec_repo.get_by_run_id(run_id)
    assert execution.current_state_name == "WaitState"
    
    # 7. Advance workflow to move past wait state to TaskB
    await advance_workflow(db_session, run_id)
    
    # 8. Find and complete the second activity task
    tasks = await activity_repo.list_by_run_id(run_id)
    assert len(tasks) == 2
    task_b = [t for t in tasks if t.activity_type == "FinalizeData"][0]
    assert task_b.status == "scheduled"
    
    # Start and complete TaskB
    await activity_service.start_task(task_b.task_token)
    await activity_service.complete_task(
        task_b.task_token, 
        json.dumps({"final": "result"})
    )
    
    # 9. Advance workflow to complete execution
    await advance_workflow(db_session, run_id)
    
    # 10. Verify workflow completed successfully
    execution = await wf_exec_repo.get_by_run_id(run_id)
    assert execution.status == "completed"
    
    # 11. Check workflow events
    from sqlalchemy import select
    stmt = select(WorkflowEvent).where(WorkflowEvent.run_id == run_id).order_by(WorkflowEvent.event_id)
    result = await db_session.execute(stmt)
    events = result.scalars().all()
    
    # Verify we have events for each state transition
    event_types = [e.event_type for e in events]
    assert "WorkflowExecutionStarted" in event_types
    assert "ActivityTaskScheduled" in event_types
    assert "TaskStateFinished" in event_types
    assert "WorkflowExecutionCompleted" in event_types
    
    # 12. Verify final workflow data
    assert execution.memo is not None
    memo_data = json.loads(execution.memo)
    assert "final" in memo_data 