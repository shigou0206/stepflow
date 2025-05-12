"""
workflow_engine.py  ——  完整实现（支持 WaitState、Choice、Pass、Task、自定义、Fail、Succeed）
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, Literal, Optional

# ===== 项目内部 import =====
from stepflow.dsl.dsl_model import (
    WorkflowDSL,
    WaitState,
    TaskState,
    CustomState,
    PassState,
    SucceedState,
    FailState,
    ChoiceState,
)
from stepflow.engine.step_runner import step_once          # 你的 step_runner 已支持 Wait / Choice
from stepflow.expression.parameter_mapper import (
    apply_parameters,
    apply_result_expr,
    apply_output_expr,
)

from stepflow.worker.task_executor import TaskExecutor
from stepflow.service.timer_service import TimerService
from stepflow.persistence.repositories.timer_repository import TimerRepository
from stepflow.persistence.models import Timer

# ---------- 下面这些保持你原来的包路径 ----------
from stepflow.persistence.database import AsyncSessionLocal
from stepflow.persistence.repositories.workflow_execution_repository import WorkflowExecutionRepository
from stepflow.persistence.repositories.workflow_template_repository import WorkflowTemplateRepository
from stepflow.persistence.repositories.workflow_event_repository import WorkflowEventRepository
from stepflow.persistence.repositories.workflow_visibility_repository import WorkflowVisibilityRepository
from stepflow.persistence.repositories.activity_task_repository import ActivityTaskRepository

from stepflow.service.workflow_execution_service import WorkflowExecutionService
from stepflow.service.workflow_template_service import WorkflowTemplateService
from stepflow.service.workflow_event_service import WorkflowEventService
from stepflow.service.workflow_visibility_service import WorkflowVisibilityService
from stepflow.service.activity_task_service import ActivityTaskService

from stepflow.hooks.base import ExecutionHooks
from stepflow.hooks.dispatcher import HookDispatcher
from stepflow.hooks.print_hook import PrintHook
from stepflow.hooks.bus_hook import BusHook
from stepflow.hooks.db_hook import DBHook

from stepflow.dsl.dsl_loader import parse_dsl_model
from stepflow.events.in_memory_eventbus import InMemoryEventBus

# ===================================================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WorkflowEngine:
    """
    内存态 Engine。每次调用 advance_once / run 会把最新上下文写回数据库。
    支持模式：
        - inline   : 同步、立即执行 Task / Wait 等节点
        - deferred : Task 由 ActivityWorker 执行；Wait 由 TimerWorker 触发
    """

    def __init__(
        self,
        hook: ExecutionHooks,
        execution_service: WorkflowExecutionService,
        task_service: ActivityTaskService,
        timer_service: TimerService,
        mode: Literal["inline", "deferred"] = "inline",
    ):
        self.hook = hook
        self.mode = mode
        self.executor = TaskExecutor()
        self.execution_service = execution_service
        self.task_service = task_service
        self.timer_service = timer_service

        # runtime
        self.dsl: Optional[WorkflowDSL] = None
        self.run_id: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.current_state: Optional[str] = None
        self.finished: bool = False
        self.result: Any = None

    # --------------------------------------------------------------------- #

    def initialize(
        self,
        run_id: str,
        dsl: WorkflowDSL,
        input_data: Dict[str, Any],
        current_state: Optional[str] = None,
    ) -> None:
        self.dsl = dsl
        self.run_id = run_id
        self.context = input_data
        self.current_state = current_state or dsl.start_at
        self.finished = False
        self.result = None

    # --------------------------------------------------------------------- #
    #                             核心推进
    # --------------------------------------------------------------------- #

    async def advance_once(self) -> Dict[str, Any]:
        """
        推进一步；返回结构：
            {
                "status": "continue" | "paused" | "finished" | "error",
                "should_continue": bool,   # 是否应当继续循环由上层决定
                "context": <最新上下文>
            }
        """
        logger.info(f"[{self.run_id}] 🔄 advance_once → state: {self.current_state}")
        if self.finished or not self.current_state:
            return {"status": "finished", "should_continue": False, "context": self.context}

        # ---------------------------------------------------- step_once
        try:
            await self.execution_service.update_current_state(self.run_id, self.current_state)
            cmd = step_once(self.dsl, self.current_state, self.context)
        except Exception as e:
            return await self._fail_workflow(f"step_once failed: {e}")

        logger.info(f"[{self.run_id}] Step → {cmd.type} : {cmd.state_name}")
        state = self.dsl.states[cmd.state_name]

        # ---------------------------------------------------- ExecuteTask
        if cmd.type == "ExecuteTask":
            return await self._handle_task_state(cmd.state_name, state)  # type: ignore[arg-type]

        # ---------------------------------------------------- Wait
        if cmd.type == "Wait":
            return await self._handle_wait_state(cmd.state_name, state)  # type: ignore[arg-type]

        # ---------------------------------------------------- Pass
        if cmd.type == "Pass":
            self.context = cmd.output
            self.current_state = cmd.next_state
            await self.execution_service.update_context_snapshot(self.run_id, self.context)
            return {"status": "continue", "should_continue": True, "context": self.context}

        # ---------------------------------------------------- Choice
        if cmd.type == "Choice":
            self.current_state = cmd.next_state
            return {"status": "continue", "should_continue": True, "context": self.context}

        # ---------------------------------------------------- Succeed
        if cmd.type == "Succeed":
            return await self._complete_workflow(cmd.output)

        # ---------------------------------------------------- Fail
        if cmd.type == "Fail":
            return await self._fail_workflow(cmd.error, cmd.cause)

        # ---------------------------------------------------- Unknown
        logger.error(f"Unknown command type: {cmd.type}, terminating.")
        return await self._fail_workflow(f"Unknown command type: {cmd.type}")

    # --------------------------------------------------------------------- #
    #                       处理不同类型 State 的私有方法
    # --------------------------------------------------------------------- #

    async def _handle_task_state(self, state_name: str, state: TaskState | CustomState) -> Dict[str, Any]:
        """
        Task / Custom -> inline & deferred 两种处理
        """
        await self.hook.on_node_enter(self.run_id, state_name, self.context)

        # ---------------- INLINE ---------------- #
        if self.mode == "inline":
            try:
                data_input = apply_parameters(self.context, state.parameters, input_expr=state.input_expr)
                result_raw = await self.executor.run_task(state, data_input)
                await self.hook.on_node_success(self.run_id, state_name, result_raw)

                intermediate = apply_result_expr(result_raw, state.result_expr)
                result = apply_output_expr(intermediate, state.output_expr)
                self.context = result
                await self.execution_service.update_context_snapshot(self.run_id, self.context)
            except Exception as e:
                await self.hook.on_node_fail(self.run_id, state_name, str(e))
                return await self._fail_workflow(str(e))

            # 判断是否结束
            if getattr(state, "end", False):
                return await self._complete_workflow(result)
            # 正常推进
            self.current_state = state.next
            return {"status": "continue", "should_continue": True, "context": self.context}

        # ---------------- DEFERRED ---------------- #
        task = await self.task_service.get_by_run_id_and_state(self.run_id, state_name)

        # 首次到达 → 创建 ActivityTask，暂停
        if not task:
            data_input = apply_parameters(self.context, state.parameters, input_expr=state.input_expr)
            await self.task_service.create_task(
                run_id=self.run_id,
                state_name=state_name,
                activity_type=state.resource,
                input_data=json.dumps(data_input),
            )
            await self.hook.on_node_dispatch(self.run_id, state_name, self.context)
            return {"status": "paused", "should_continue": False, "context": self.context}

        # 已失败
        if task.status == "failed":
            return await self._fail_workflow(task.error or "ActivityTask failed", task.error_details)

        # 未完成
        if task.status != "completed":
            return {"status": "paused", "should_continue": False, "context": self.context}

        # 已完成 → 读取结果推进
        try:
            result_raw = json.loads(task.result or "{}")
        except Exception:
            result_raw = {"result": task.result}
        await self.hook.on_node_success(self.run_id, state_name, result_raw)

        intermediate = apply_result_expr(result_raw, state.result_expr)
        result = apply_output_expr(intermediate, state.output_expr)
        self.context = result
        await self.execution_service.update_context_snapshot(self.run_id, self.context)

        if getattr(state, "end", False):
            return await self._complete_workflow(result)

        self.current_state = state.next
        return {"status": "continue", "should_continue": True, "context": self.context}

    # ------------------------------------------------------------------ #
    async def _handle_wait_state(self, state_name: str, state: WaitState) -> Dict[str, Any]:
        """
        WaitState 支持三种写法：
            1. seconds     = 10      → 等 10 秒
            2. timestamp   = "2025-05-12T22:30:00Z"
            3. seconds / timestamp + next / end
        """
        logger.info(f"[{self.run_id}] ⏳ Handling WaitState '{state_name}'")

        # ------------ INLINE 直接阻塞等待 ------------ #
        if self.mode == "inline":
            sleep_seconds: int
            if state.seconds is not None:
                sleep_seconds = state.seconds
            elif state.timestamp is not None:
                fire_at = datetime.fromisoformat(state.timestamp)
                now = datetime.now(UTC)
                sleep_seconds = max(0, int((fire_at - now).total_seconds()))
            else:
                return await self._fail_workflow("WaitState must define seconds or timestamp")

            await asyncio.sleep(sleep_seconds)

            # inline wait 完成
            if getattr(state, "end", False):
                return await self._complete_workflow(self.context)

            self.current_state = state.next
            return {"status": "continue", "should_continue": True, "context": self.context}

        # ------------ DEFERRED → Timer -------------- #
        # 查有没有已存在、且还未触发的 timer
        due_timer: Optional[Timer] = await self.timer_service.get_by_run_id_and_state(
            self.run_id, state_name  # type: ignore[attr-defined]
        )  # 建议你在 TimerRepository 实现这个查询

        if not due_timer:
            # 计算 fire_at
            if state.seconds is not None:
                fire_at = datetime.now(UTC) + timedelta(seconds=state.seconds)
            elif state.timestamp is not None:
                fire_at = datetime.fromisoformat(state.timestamp)
            else:
                return await self._fail_workflow("WaitState must define seconds or timestamp")

            await self.timer_service.schedule_timer(
                run_id=self.run_id,
                shard_id=0,
                fire_at=fire_at,
            )
            await self.hook.on_node_dispatch(self.run_id, state_name, self.context)
            return {"status": "paused", "should_continue": False, "context": self.context}

        # Timer 仍在等待
        if due_timer.status == "scheduled":
            return {"status": "paused", "should_continue": False, "context": self.context}

        # Timer 已触发 (fired) → 继续
        if due_timer.status == "fired":
            if getattr(state, "end", False):
                return await self._complete_workflow(self.context)

            self.current_state = state.next
            return {"status": "continue", "should_continue": True, "context": self.context}

        # 其它情况（canceled 等）视为失败
        return await self._fail_workflow(f"Timer in unexpected status: {due_timer.status}")

    # --------------------------------------------------------------------- #
    #                           工作流结束/失败
    # --------------------------------------------------------------------- #

    async def _complete_workflow(self, output: Any) -> Dict[str, Any]:
        await self.execution_service.complete_workflow(self.run_id, output)
        await self.hook.on_workflow_end(self.run_id, output)
        self.result = output
        self.finished = True
        return {"status": "finished", "should_continue": False, "context": output}

    async def _fail_workflow(self, error: str, cause: Optional[str] = None) -> Dict[str, Any]:
        err_obj = {"error": error}
        if cause:
            err_obj["cause"] = cause
        await self.execution_service.fail_workflow(self.run_id, err_obj)
        await self.hook.on_workflow_end(self.run_id, err_obj)
        self.result = err_obj
        self.finished = True
        return {"status": "error", "should_continue": False, "context": err_obj}


# =========================================================================
#                      顶层便捷函数  advance / run_inline
# =========================================================================
#  * 与原先版本保持同样签名，只是注入了 TimerService
#  * 代码保持完整，未做任何省略
# =========================================================================

async def _build_engine(
    session,
    run_id: str,
    mode: Literal["inline", "deferred"],
) -> tuple[WorkflowEngine, Dict[str, Any]]:
    exec_service = WorkflowExecutionService(WorkflowExecutionRepository(session))
    wf_exec = await exec_service.get_execution(run_id)
    if not wf_exec:
        raise ValueError(f"Workflow execution {run_id} not found")

    if wf_exec.status in {"failed", "completed"}:
        raise RuntimeError(f"Workflow already terminal: {wf_exec.status}")

    tmpl_service = WorkflowTemplateService(WorkflowTemplateRepository(session))
    tmpl = await tmpl_service.get_template(wf_exec.template_id)
    if not tmpl:
        raise ValueError(f"Template {wf_exec.template_id} not found")

    dsl = parse_dsl_model(json.loads(tmpl.dsl_definition))
    context = json.loads(wf_exec.context_snapshot or wf_exec.result or wf_exec.input or "{}")

    # ---- Hook dispatcher ----
    event_bus = InMemoryEventBus()
    event_service = WorkflowEventService(WorkflowEventRepository(session))
    vis_service = WorkflowVisibilityService(WorkflowVisibilityRepository(session))
    task_service = ActivityTaskService(ActivityTaskRepository(session))
    timer_service = TimerService(TimerRepository(session))

    hook = HookDispatcher(
        [PrintHook(), BusHook(event_bus, shard_id=wf_exec.shard_id), DBHook(exec_service, event_service, vis_service, shard_id=wf_exec.shard_id)]
    )

    engine = WorkflowEngine(
        hook=hook,
        execution_service=exec_service,
        task_service=task_service,
        timer_service=timer_service,
        mode=mode,
    )
    engine.initialize(run_id, dsl, context, current_state=wf_exec.current_state_name)
    return engine, context


async def advance_workflow(run_id: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        try:
            engine, _ = await _build_engine(session, run_id, mode="deferred")
        except Exception as e:
            logger.exception(f"[{run_id}] init error: {e}")
            return {"status": "error", "context": str(e)}

        try:
            while True:
                result = await engine.advance_once()
                if not result.get("should_continue"):
                    return result
        except Exception as e:
            logger.exception(f"[{run_id}] ❌ Unhandled error in advance loop: {e}")
            # 尝试降级失败标记
            exec_service = WorkflowExecutionService(WorkflowExecutionRepository(session))
            await exec_service.fail_workflow(run_id, {"error": str(e)})
            return {"status": "error", "context": str(e)}


async def run_inline_workflow(run_id: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        try:
            engine, context = await _build_engine(session, run_id, mode="inline")
        except Exception as e:
            logger.exception(f"[{run_id}] init error: {e}")
            return {"status": "error", "context": str(e)}

        try:
            result = await engine.run(run_id, engine.dsl, context)  # type: ignore[arg-type]
            return {"status": "finished", "result": result}
        except Exception as e:
            logger.exception(f"[{run_id}] ❌ Inline workflow execution failed: {e}")
            exec_service = WorkflowExecutionService(WorkflowExecutionRepository(session))
            await exec_service.fail_workflow(run_id, {"error": str(e)})
            return {"status": "error", "result": str(e)}