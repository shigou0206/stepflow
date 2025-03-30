# stepflow/domain/engine/replay_async.py

import json
from typing import Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from stepflow.domain.dsl_model import WorkflowDSL
from stepflow.domain.engine.execution_engine import parse_workflow_dsl  # or local parse function
from stepflow.infrastructure.models import WorkflowExecution, WorkflowTemplate, WorkflowEvent

async def replay_workflow(db: AsyncSession, run_id: str) -> Tuple[Dict, str]:
    """
    从 event_id=1 开始顺序读取 events, 模拟工作流状态流转, 构建最终上下文 & 状态
    返回 (context, status)
    """
    # 1) 获取 workflow_executions
    stmt_exec = select(WorkflowExecution).where(WorkflowExecution.run_id == run_id)
    result_exec = await db.execute(stmt_exec)
    wf_exec = result_exec.scalar_one_or_none()
    if not wf_exec:
        return {}, "not_found"

    # 2) 获取 template, parse DSL
    stmt_tpl = select(WorkflowTemplate).where(WorkflowTemplate.template_id == wf_exec.template_id)
    result_tpl = await db.execute(stmt_tpl)
    tpl = result_tpl.scalar_one_or_none()
    if not tpl:
        return {}, "template_missing"

    # 如果 parse_workflow_dsl 是纯同步(只是json.loads),
    # 也可以不加 async. 这里假设它是 async.
    dsl: WorkflowDSL = await parse_workflow_dsl(tpl.dsl_definition)

    # 3) 初始化上下文
    #    通常从 wf_exec.input (JSON字符串) 中取
    context_str = wf_exec.input
    if not context_str:
        context = {}
    else:
        try:
            context = json.loads(context_str)
        except:
            context = {}

    # 初始状态: dsl.StartAt, 也可先从 event 回放
    current_state_name = dsl.StartAt
    status = "running"

    # 4) 顺序读 events
    stmt_evt = (
        select(WorkflowEvent)
        .where(WorkflowEvent.run_id == run_id)
        .order_by(WorkflowEvent.id.asc())
    )
    result_evt = await db.execute(stmt_evt)
    events = result_evt.scalars().all()

    for evt in events:
        etype = evt.event_type
        attr_str = evt.attributes or "{}"
        try:
            attr = json.loads(attr_str)
        except:
            attr = {}

        # 根据 etype 做回放逻辑
        if etype == "WorkflowExecutionStarted":
            # 如果 attributes 里有 'input': {...}, 可 merge到context
            pass
        elif etype == "TaskStateFinished":
            # attr = {"next":"Step2","result":{...}}
            res = attr.get("result")
            if res:
                # merge res into context
                # (可用 set_value_by_path 等, 这里只是示例)
                pass
            # next state
            next_state = attr.get("next")
            if next_state:
                current_state_name = next_state

        elif etype == "WorkflowExecutionSucceeded":
            status = "completed"
            break
        elif etype == "WorkflowExecutionFailed":
            status = "failed"
            break

        # 其它事件: "ActivityTaskScheduled", "TimerFired", "ChoiceMatched" ...
        # 可以逐个解析 attr 并模拟当时状态

    return (context, status)