# stepflow/domain/engine/execution_engine_async.py

import json
import asyncio
import logging
from typing import Optional
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from stepflow.domain.dsl_model import (
    WorkflowDSL, StateUnion, TaskState, ChoiceState,
    WaitState, ParallelState, PassState, FailState, SucceedState
)
from stepflow.domain.engine.path_utils import get_value_by_path, set_value_by_path

from stepflow.infrastructure.models import (
    WorkflowExecution, WorkflowTemplate, ActivityTask, WorkflowEvent,
    WorkflowVisibility
)
from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.infrastructure.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.infrastructure.repositories.workflow_visibility_repository import WorkflowVisibilityRepository

logger = logging.getLogger(__name__)

async def parse_workflow_dsl(dsl_text: str) -> WorkflowDSL:
    data = json.loads(dsl_text)
    return WorkflowDSL(**data)

async def advance_workflow(db: AsyncSession, run_id: str) -> None:
    """推进工作流执行"""
    # 获取工作流执行
    exec_repo = WorkflowExecutionRepository(db)
    wf_exec = await exec_repo.get_by_run_id(run_id)
    
    # 如果工作流已经完成或失败，则不需要推进
    if wf_exec.status in ["completed", "failed", "canceled"]:
        return
    
    # 获取工作流模板
    tpl_repo = WorkflowTemplateRepository(db)
    try:
        tpl = await tpl_repo.get_by_id(wf_exec.template_id)
        if not tpl:
            print(f"Warning: Template {wf_exec.template_id} not found")
            return
    except Exception as e:
        print(f"Error getting template: {str(e)}")
        return
    
    # 解析 DSL
    # 先拿 template
    dsl = await parse_workflow_dsl(tpl.dsl_definition)

    # 当前状态名
    current_state_name = wf_exec.current_state_name
    if not current_state_name:
        # 首次执行
        current_state_name = dsl.StartAt
        wf_exec.current_state_name = current_state_name
        await exec_repo.update(wf_exec)

    state_def = dsl.States[current_state_name]

    # 根据类型分发
    if isinstance(state_def, TaskState):
        await handle_task_state(db, wf_exec, dsl, state_def)
    elif isinstance(state_def, ChoiceState):
        await handle_choice_state(db, wf_exec, dsl, state_def)
    elif isinstance(state_def, WaitState):
        await handle_wait_state(db, wf_exec, dsl, state_def)
    elif isinstance(state_def, ParallelState):
        await handle_parallel_state(db, wf_exec, dsl, state_def)
    elif isinstance(state_def, PassState):
        await handle_pass_state(db, wf_exec, dsl, state_def)
    elif isinstance(state_def, FailState):
        await handle_fail_state(db, wf_exec, state_def)
    elif isinstance(state_def, SucceedState):
        await handle_succeed_state(db, wf_exec)

    # 提交
    await db.commit()

async def handle_task_state(db: AsyncSession, wf_exec: WorkflowExecution, dsl: WorkflowDSL, state_def: TaskState):
    # 读取上下文
    memo_json = json.loads(wf_exec.memo) if wf_exec.memo else {}
    node_input = get_value_by_path(memo_json, state_def.InputPath)

    # 查询是否已存在活动任务
    stmt = select(ActivityTask).where(
        ActivityTask.run_id == wf_exec.run_id,
        ActivityTask.activity_type == state_def.ActivityType
    )
    result = await db.execute(stmt)
    act_task: ActivityTask = result.scalar_one_or_none()

    if not act_task:
        # 还没调度 => 创建, status='scheduled'
        from uuid import uuid4
        new_token = str(uuid4())
        act_task = ActivityTask(
            task_token=new_token,
            run_id=wf_exec.run_id,
            shard_id=wf_exec.shard_id,
            activity_type=state_def.ActivityType,
            status="scheduled",
            input=json.dumps(node_input),
            scheduled_at=datetime.now(UTC)
        )
        db.add(act_task)

        # 记事件
        new_evt = WorkflowEvent(
            run_id=wf_exec.run_id,
            shard_id=wf_exec.shard_id,
            event_id=0,
            event_type="ActivityTaskScheduled",
            attributes=json.dumps({"activity_type": state_def.ActivityType})
        )
        db.add(new_evt)

        await db.commit()  # 提交
        return  # 等外部回调 => 下次 advance_workflow

    # 如果找到, 看其 status
    if act_task.status == "running":
        # 还没完成 => 先不推进
        return
    elif act_task.status == "completed":
        # 拿 result
        result_data = {}
        if act_task.result:
            result_data = json.loads(act_task.result)

        # 合并 => ResultPath
        merged = set_value_by_path(memo_json, state_def.ResultPath, result_data)
        # => OutputPath
        out_data = get_value_by_path(merged, state_def.OutputPath)
        if not isinstance(out_data, dict):
            out_data = {"value": out_data}
        wf_exec.memo = json.dumps(out_data)

        # 结束 or Next
        if state_def.End:
            wf_exec.status = "completed"
            wf_exec.close_time = datetime.now(UTC)
            new_evt = WorkflowEvent(
                run_id=wf_exec.run_id,
                shard_id=wf_exec.shard_id,
                event_id=0,
                event_type="WorkflowExecutionCompleted"
            )
            db.add(new_evt)
        elif state_def.Next:
            wf_exec.current_state_name = state_def.Next
            evt = WorkflowEvent(
                run_id=wf_exec.run_id,
                shard_id=wf_exec.shard_id,
                event_id=0,
                event_type="TaskStateFinished",
                attributes=json.dumps({"next": state_def.Next})
            )
            db.add(evt)
        # else => error?
    elif act_task.status == "failed":
        # 看 Retry/Catch or fail
        # 简化: 直接 fail
        wf_exec.status = "failed"
        wf_exec.close_time = datetime.now(UTC)
        fail_evt = WorkflowEvent(
            run_id=wf_exec.run_id,
            shard_id=wf_exec.shard_id,
            event_id=0,
            event_type="ActivityTaskFailed"
        )
        db.add(fail_evt)
    # 其余: timed_out, canceled...

    # 提交
    await db.commit()

async def handle_choice_state(db: AsyncSession, wf_exec: WorkflowExecution, dsl: WorkflowDSL, state_def: ChoiceState):
    memo_json = json.loads(wf_exec.memo) if wf_exec.memo else {}
    choice_input = get_value_by_path(memo_json, state_def.InputPath) or {}
    next_state = None
    for c in state_def.Choices:
        val = get_value_by_path(choice_input, c.Variable)
        if val == c.StringEquals:
            next_state = c.Next
            break
    if not next_state and state_def.Default:
        next_state = state_def.Default

    if not next_state:
        # no match => fail
        wf_exec.status = "failed"
        wf_exec.close_time = datetime.now(UTC)
        new_evt = WorkflowEvent(
            run_id=wf_exec.run_id,
            shard_id=wf_exec.shard_id,
            event_id=0,
            event_type="ChoiceNoMatch"
        )
        db.add(new_evt)
    else:
        wf_exec.current_state_name = next_state
        new_evt = WorkflowEvent(
            run_id=wf_exec.run_id,
            shard_id=wf_exec.shard_id,
            event_id=0,
            event_type="ChoiceMatched",
            attributes=json.dumps({"next": next_state})
        )
        db.add(new_evt)

    await db.commit()

async def handle_wait_state(db: AsyncSession, wf_exec: WorkflowExecution, dsl: WorkflowDSL, state_def: WaitState):
    # 省略: 可能要看 timers
    if state_def.End:
        wf_exec.status = "completed"
        wf_exec.close_time = datetime.now(UTC)
    elif state_def.Next:
        wf_exec.current_state_name = state_def.Next

    await db.commit()

async def handle_parallel_state(db: AsyncSession, wf_exec: WorkflowExecution, dsl: WorkflowDSL, state_def: ParallelState):
    # 并行分支 => 需要自定义
    # ...
    await db.commit()

async def handle_pass_state(db: AsyncSession, wf_exec: WorkflowExecution, dsl: WorkflowDSL, state_def: PassState):
    memo_json = json.loads(wf_exec.memo) if wf_exec.memo else {}
    if state_def.Result:
        merged = set_value_by_path(memo_json, state_def.ResultPath, state_def.Result)
    else:
        merged = memo_json
    out_data = get_value_by_path(merged, state_def.OutputPath)
    if not isinstance(out_data, dict):
        out_data = {"value": out_data}
    wf_exec.memo = json.dumps(out_data)
    if state_def.End:
        wf_exec.status = "completed"
        wf_exec.close_time = datetime.now(UTC)
    elif state_def.Next:
        wf_exec.current_state_name = state_def.Next

    await db.commit()

async def handle_fail_state(db: AsyncSession, wf_exec: WorkflowExecution, state_def: FailState):
    wf_exec.status = "failed"
    wf_exec.close_time = datetime.now(UTC)
    new_evt = WorkflowEvent(
        run_id=wf_exec.run_id,
        shard_id=wf_exec.shard_id,
        event_id=0,
        event_type="WorkflowExecutionFailed",
        attributes=json.dumps({"error": state_def.Error, "cause": state_def.Cause})
    )
    db.add(new_evt)
    await db.commit()

async def handle_succeed_state(db: AsyncSession, wf_exec: WorkflowExecution):
    wf_exec.status = "completed"
    wf_exec.close_time = datetime.now(UTC)
    new_evt = WorkflowEvent(
        run_id=wf_exec.run_id,
        shard_id=wf_exec.shard_id,
        event_id=0,
        event_type="WorkflowExecutionSucceeded"
    )
    db.add(new_evt)
    await db.commit()

async def handle_activity_task_failed(task_token: str, reason: str, details: Optional[str] = None) -> None:
    """处理活动任务失败"""
    # 创建仓库
    from stepflow.infrastructure.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        activity_repo = ActivityTaskRepository(session)
        execution_repo = WorkflowExecutionRepository(session)
        event_repo = WorkflowEventRepository(session)
        visibility_repo = WorkflowVisibilityRepository(session)
        
        # 获取任务
        task = await activity_repo.get_by_token(task_token)
        if not task:
            logger.error(f"活动任务失败处理: 找不到任务 {task_token}")
            return
        
        # 获取工作流执行
        execution = await execution_repo.get_by_run_id(task.run_id)
        if not execution:
            logger.error(f"活动任务失败处理: 找不到工作流执行 {task.run_id}")
            return
        
        # 记录任务失败事件
        await event_repo.create_event(
            run_id=task.run_id,
            event_type="ACTIVITY_TASK_FAILED",
            event_data=json.dumps({
                "task_token": task_token,
                "activity_type": task.activity_type,
                "reason": reason,
                "details": details
            })
        )
        
        # 更新工作流执行状态为失败
        execution.status = "failed"
        execution.end_time = datetime.now(UTC)
        execution.result = json.dumps({
            "error": f"Activity task failed: {reason}",
            "details": details
        })
        await execution_repo.update(execution)
        
        # 更新工作流可见性
        visibility = await visibility_repo.get_by_run_id(task.run_id)
        if visibility:
            visibility.status = "failed"
            visibility.end_time = datetime.now(UTC)
            await visibility_repo.update(visibility)
        
        logger.info(f"工作流 {task.run_id} 因活动任务 {task_token} 失败而终止: {reason}")