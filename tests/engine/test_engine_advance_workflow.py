import pytest
import pytest_asyncio
import json
from stepflow.dsl.dsl_model import WorkflowDSL
from stepflow.dsl.dsl_loader import parse_dsl_model
from stepflow.persistence.database import AsyncSessionLocal, async_engine, Base
from stepflow.persistence.models import WorkflowTemplate
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.persistence.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.service.workflow_execution_service import WorkflowExecutionService
from stepflow.engine.workflow_engine import advance_workflow

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # async with async_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    async with AsyncSessionLocal() as db:
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_advance_workflow_inline_one_step():
    async with AsyncSessionLocal() as session:
        # 准备 DSL 模型（仅一步）
        dsl_def = {
            "StartAt": "Start",
            "States": {
                "Start": {
                    "Type": "Pass",
                    "Result": {"msg": "done"},
                    "ResultPath": "$.msg",
                    "End": True
                }
            }
        }
        dsl_str = json.dumps(dsl_def, ensure_ascii=False)
        dsl_model = parse_dsl_model(dsl_def)

        # 写入模板
        template_repo = WorkflowTemplateRepository(session)
        template = WorkflowTemplate(
            template_id="tpl-001",
            name="Test Template",
            dsl_definition=dsl_str
        )
        await template_repo.create(template)

        # 启动执行
        exec_service = WorkflowExecutionService(WorkflowExecutionRepository(session))
        wf_exec = await exec_service.start_workflow(
            template_id="tpl-001",
            initial_input={"x": 1},
            mode="inline"
        )

        # 设置当前状态（默认已是 Start）
        wf_exec.current_state_name = dsl_model.start_at
        await session.commit()

        # 执行推进
        result = await advance_workflow(wf_exec.run_id)

        # 校验结果
        assert result["status"] == "finished"
        assert result["context"] == {"msg": "done"}

@pytest.mark.asyncio
async def test_advance_workflow_deferred_mode_dispatch():
    async with AsyncSessionLocal() as session:
        dsl_def = {
            "StartAt": "StepA",
            "States": {
                "StepA": {
                    "Type": "Task",
                    "Resource": "DummyTool",
                    "Parameters": {"value": 10},
                    "End": True
                }
            }
        }
        dsl_str = json.dumps(dsl_def, ensure_ascii=False)
        dsl_model = parse_dsl_model(dsl_def)

        template_repo = WorkflowTemplateRepository(session)
        await template_repo.create(WorkflowTemplate(
            template_id="tpl-002",
            name="Test Deferred Template",
            dsl_definition=dsl_str
        ))

        exec_service = WorkflowExecutionService(WorkflowExecutionRepository(session))
        wf_exec = await exec_service.start_workflow(
            template_id="tpl-002",
            initial_input={"x": 42},
            mode="deferred"
        )
        wf_exec.current_state_name = dsl_model.start_at
        await session.commit()

        result = await advance_workflow(wf_exec.run_id)

        assert result["status"] == "paused"
        assert result["context"] == {"x": 42}