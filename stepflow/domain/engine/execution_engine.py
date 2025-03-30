# stepflow/domain/engine/execution_engine_async.py

import json
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
    WorkflowExecution, WorkflowTemplate, ActivityTask, WorkflowEvent
)

async def parse_workflow_dsl(dsl_text: str) -> WorkflowDSL:
    data = json.loads(dsl_text)
    return WorkflowDSL(**data)

async def advance_workflow(db: AsyncSession, run_id: str):
    """
    主调度 (异步): 
    1. 从 DB 找 workflow_executions,
    2. 若 status=running -> parse DSL,
    3. 根据当前状态分发 handle_xxx_state,
    4. commit
    """
    stmt_exec = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
    result = await db.execute(stmt_exec)
    wf_exec: WorkflowExecution = result.scalar_one_or_none()
    if not wf_exec or wf_exec.status not in ["running"]:
        return  # do nothing

    # 解析 DSL
    # 先拿 template
    stmt_tpl = select(WorkflowTemplate).where(WorkflowTemplate.template_id == wf_exec.template_id)
    tpl_result = await db.execute(stmt_tpl)
    tpl = tpl_result.scalar_one()
    dsl = await parse_workflow_dsl(tpl.dsl_definition)

    # 当前状态名
    current_state = wf_exec.current_state_name
    if not current_state:
        # 首次执行
        current_state = dsl.StartAt
        wf_exec.current_state_name = current_state

    state_def = dsl.States[current_state]

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