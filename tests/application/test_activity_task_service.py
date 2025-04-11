import pytest
import pytest_asyncio
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.application.activity_task_service import ActivityTaskService
from stepflow.infrastructure.models import ActivityTask
import uuid
from datetime import datetime, UTC

@pytest_asyncio.fixture(scope="module")
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
async def test_schedule_and_start(db_session):
    # 1) 创建仓库
    repo = ActivityTaskRepository(db_session)
    # 2) 创建Service, 注入仓库
    svc = ActivityTaskService(repo)

    # 3) 创建一个任务 - 不使用 created_at 参数
    task = ActivityTask(
        task_token=str(uuid.uuid4()),
        run_id="run-xyz",
        shard_id=1,
        seq=1,
        activity_type="test_type",
        input="{}",
        status="scheduled"
        # 不设置 scheduled_at，让数据库默认值处理
    )
    
    # 保存任务
    created_task = await repo.create(task)
    
    # 4) 启动任务
    started_task = await svc.start_task(created_task.task_token)
    
    # 5) 验证任务状态
    assert started_task.status == "running"
    assert started_task.started_at is not None

@pytest.mark.asyncio
async def test_complete_task(db_session):
    repo = ActivityTaskRepository(db_session)
    svc = ActivityTaskService(repo)
    
    # 创建一个任务 - 不使用 created_at 和 started_at 参数
    task = ActivityTask(
        task_token=str(uuid.uuid4()),
        run_id="run-xyz",
        shard_id=1,
        seq=1,
        activity_type="test_type",
        input="{}",
        status="running"
        # 不设置时间戳
    )
    
    # 保存任务
    created_task = await repo.create(task)
    
    # 完成任务
    completed_task = await svc.complete_task(
        created_task.task_token,
        result_data='{"result":"success"}'
    )
    
    # 验证任务状态
    assert completed_task.status == "completed"
    assert completed_task.completed_at is not None
    assert completed_task.result == '{"result":"success"}'

@pytest.mark.asyncio
async def test_fail_task(db_session):
    repo = ActivityTaskRepository(db_session)
    svc = ActivityTaskService(repo)
    
    # 创建一个任务 - 不使用 created_at 和 started_at 参数
    task = ActivityTask(
        task_token=str(uuid.uuid4()),
        run_id="run-zzz",
        shard_id=2,
        seq=2,
        activity_type="failing_activity",
        input="{}",
        status="running"
        # 不设置时间戳
    )
    
    # 保存任务
    created_task = await repo.create(task)
    
    # 标记任务失败
    failed_task = await svc.fail_task(
        created_task.task_token,
        reason="Test failure",
        details="Detailed error information"
    )
    
    # 验证任务状态
    assert failed_task.status == "failed"
    assert failed_task.completed_at is not None
    assert failed_task.error == "Test failure"
    assert failed_task.error_details == "Detailed error information"