"""
workflow_engine.py —— 完整实现（支持 Wait / Choice / Pass / Task / Custom / Fail / Succeed）
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, Literal, Optional

# ===== DSL & utils =====
from stepflow.dsl.dsl_model import (
    WorkflowDSL,
    WaitState,
    TaskState,
    CustomState,
)
from stepflow.engine.step_runner import step_once
from stepflow.expression.parameter_mapper import (
    apply_parameters,
    apply_result_expr,
    apply_output_expr,
)

# ===== Services & repos =====
from stepflow.worker.task_executor import TaskExecutor
from stepflow.service.timer_service import TimerService
from stepflow.persistence.repositories.timer_repository import TimerRepository
from stepflow.persistence.models import Timer
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

# ===== Hooks =====
from stepflow.hooks.base import ExecutionHooks
from stepflow.hooks.dispatcher import HookDispatcher
from stepflow.hooks.print_hook import PrintHook
from stepflow.hooks.bus_hook import BusHook
from stepflow.hooks.db_hook import DBHook

from stepflow.utils.timefmt import to_utc_naive

# ===== Others =====
from stepflow.dsl.dsl_loader import parse_dsl_model
from stepflow.events.in_memory_eventbus import InMemoryEventBus

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ──────────────────────────────────────────────────────────────────────────
#                              WorkflowEngine
# ──────────────────────────────────────────────────────────────────────────
class WorkflowEngine:
    """
    内存态 Engine：
      - inline   : Task/Wait 同步执行
      - deferred : Task 走 ActivityWorker，Wait 走 TimerWorker
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

    # ------------------------------------------------------------------ #
    #                           public helpers
    # ------------------------------------------------------------------ #
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

    async def run(self, run_id: str, dsl: WorkflowDSL, input_data: Dict[str, Any]) -> Any:
        """Inline -> 一口气跑到底。"""
        if self.mode != "inline":
            raise RuntimeError("run() is only supported in inline mode")

        if self.dsl is None or not self.context:
            self.initialize(run_id, dsl, input_data)

        logger.info(f"[{self.run_id}] ▶️ start inline run()")
        while True:
            res = await self.advance_once()
            if not res["should_continue"]:
                logger.info(f"[{self.run_id}] 🛑 finished -> {res['context']}")
                return res["context"]

    # ------------------------------------------------------------------ #
    #                          core step loop
    # ------------------------------------------------------------------ #
    async def advance_once(self) -> Dict[str, Any]:
        logger.info(f"[{self.run_id}] 🔄 advance_once → {self.current_state}")

        if self.finished or not self.current_state:
            return {"status": "finished", "should_continue": False, "context": self.context}

        # step_once
        try:
            await self.execution_service.update_current_state(self.run_id, self.current_state)
            cmd = step_once(self.dsl, self.current_state, self.context)
        except Exception as exc:
            return await self._fail_workflow(f"step_once failed: {exc}")

        logger.info(f"[{self.run_id}] Step → {cmd.type} : {cmd.state_name}")
        state = self.dsl.states[cmd.state_name]

        match cmd.type:
            case "ExecuteTask":
                return await self._handle_task_state(cmd.state_name, state)  # type: ignore[arg-type]
            case "Wait":
                return await self._handle_wait_state(cmd.state_name, state)  # type: ignore[arg-type]
            case "Pass":
                self.context = cmd.output
                self.current_state = cmd.next_state
                await self.execution_service.update_context_snapshot(self.run_id, self.context)
                return {"status": "continue", "should_continue": True, "context": self.context}
            case "Choice":
                self.current_state = cmd.next_state
                return {"status": "continue", "should_continue": True, "context": self.context}
            case "Succeed":
                return await self._complete_workflow(cmd.output)
            case "Fail":
                return await self._fail_workflow(cmd.error, cmd.cause)
            case _:
                return await self._fail_workflow(f"Unknown command type: {cmd.type}")

    # ------------------------------------------------------------------ #
    #                       state-type handlers
    # ------------------------------------------------------------------ #
    async def _handle_task_state(self, state_name: str, state: TaskState | CustomState) -> Dict[str, Any]:
        await self.hook.on_node_enter(self.run_id, state_name, self.context)

        # ---------- inline ----------
        if self.mode == "inline":
            try:
                inp = apply_parameters(self.context, state.parameters, input_expr=state.input_expr)
                raw = await self.executor.run_task(state, inp)
                await self.hook.on_node_success(self.run_id, state_name, raw)

                inter = apply_result_expr(raw, state.result_expr)
                res = apply_output_expr(inter, state.output_expr)
                self.context = res
                await self.execution_service.update_context_snapshot(self.run_id, self.context)
            except Exception as exc:
                await self.hook.on_node_fail(self.run_id, state_name, str(exc))
                return await self._fail_workflow(str(exc))

            if getattr(state, "end", False):
                return await self._complete_workflow(res)

            self.current_state = state.next
            return {"status": "continue", "should_continue": True, "context": self.context}

        # ---------- deferred ----------
        task = await self.task_service.get_by_run_id_and_state(self.run_id, state_name)
        if not task:
            inp = apply_parameters(self.context, state.parameters, input_expr=state.input_expr)
            await self.task_service.create_task(
                run_id=self.run_id,
                state_name=state_name,
                activity_type=state.resource,
                input_data=json.dumps(inp),
            )
            await self.hook.on_node_dispatch(self.run_id, state_name, self.context)
            return {"status": "paused", "should_continue": False, "context": self.context}

        if task.status == "failed":
            return await self._fail_workflow(task.error or "ActivityTask failed", task.error_details)

        if task.status != "completed":
            return {"status": "paused", "should_continue": False, "context": self.context}

        try:
            raw = json.loads(task.result or "{}")
        except Exception:
            raw = {"result": task.result}

        await self.hook.on_node_success(self.run_id, state_name, raw)
        inter = apply_result_expr(raw, state.result_expr)
        res = apply_output_expr(inter, state.output_expr)
        self.context = res
        await self.execution_service.update_context_snapshot(self.run_id, self.context)

        if getattr(state, "end", False):
            return await self._complete_workflow(res)

        self.current_state = state.next
        return {"status": "continue", "should_continue": True, "context": self.context}

    # ------------------------------------------------------------------ #
    async def _handle_wait_state(self, state_name: str, state: WaitState) -> Dict[str, Any]:
        logger.info(f"[{self.run_id}] ⏳ wait '{state_name}'")

        # ---------- inline ----------
        if self.mode == "inline":
            if state.seconds is not None:
                await asyncio.sleep(state.seconds)
            elif state.timestamp is not None:
                diff = datetime.fromisoformat(state.timestamp) - datetime.now(UTC)
                await asyncio.sleep(max(0, int(diff.total_seconds())))
            else:
                return await self._fail_workflow("WaitState must define seconds or timestamp")

            if getattr(state, "end", False):
                return await self._complete_workflow(self.context)

            self.current_state = state.next
            return {"status": "continue", "should_continue": True, "context": self.context}

        # ---------- deferred ----------
        due_timer: Optional[Timer] = await self.timer_service.get_by_run_id_and_state(self.run_id, state_name)

        if not due_timer:
            if state.seconds is not None:
                fire_at = to_utc_naive(datetime.now(UTC) + timedelta(seconds=state.seconds))
            elif state.timestamp is not None:
                dt = datetime.fromisoformat(state.timestamp)
                fire_at = to_utc_naive(dt)
            else:
                return await self._fail_workflow("WaitState must define seconds or timestamp")

            await self.timer_service.schedule_timer(
                run_id=self.run_id,
                state_name=state_name,   # ← 修正：补充 state_name
                shard_id=0,
                fire_at=fire_at,
            )
            await self.hook.on_node_dispatch(self.run_id, state_name, self.context)
            return {"status": "paused", "should_continue": False, "context": self.context}

        if due_timer.status == "scheduled":
            return {"status": "paused", "should_continue": False, "context": self.context}

        if due_timer.status == "fired":
            if getattr(state, "end", False):
                return await self._complete_workflow(self.context)

            self.current_state = state.next
            return {"status": "continue", "should_continue": True, "context": self.context}

        return await self._fail_workflow(f"Timer status invalid: {due_timer.status}")

    # ------------------------------------------------------------------ #
    async def _complete_workflow(self, output: Any) -> Dict[str, Any]:
        await self.execution_service.complete_workflow(self.run_id, output)
        await self.hook.on_workflow_end(self.run_id, output)
        self.finished, self.result = True, output
        return {"status": "finished", "should_continue": False, "context": output}

    async def _fail_workflow(self, error: str, cause: Optional[str] = None) -> Dict[str, Any]:
        err_obj = {"error": error, **({"cause": cause} if cause else {})}
        await self.execution_service.fail_workflow(self.run_id, err_obj)
        await self.hook.on_workflow_end(self.run_id, err_obj)
        self.finished, self.result = True, err_obj
        return {"status": "error", "should_continue": False, "context": err_obj}


# ──────────────────────────────────────────────────────────────────────────
#                        builder & helper runners
# ──────────────────────────────────────────────────────────────────────────
async def _build_engine(session, run_id: str, mode: Literal["inline", "deferred"]) -> tuple[WorkflowEngine, Dict[str, Any]]:
    exec_svc = WorkflowExecutionService(WorkflowExecutionRepository(session))
    wf_exec = await exec_svc.get_execution(run_id)
    if not wf_exec:
        raise ValueError(f"workflow {run_id} not found")
    if wf_exec.status in {"failed", "completed"}:
        raise RuntimeError(f"Workflow already terminal: {wf_exec.status}")

    tmpl_svc = WorkflowTemplateService(WorkflowTemplateRepository(session))
    tmpl = await tmpl_svc.get_template(wf_exec.template_id)
    if not tmpl:
        raise ValueError(f"template {wf_exec.template_id} not found")

    dsl = parse_dsl_model(json.loads(tmpl.dsl_definition))
    ctx = json.loads(wf_exec.context_snapshot or wf_exec.result or wf_exec.input or "{}")

    # hooks
    event_bus = InMemoryEventBus()
    hook = HookDispatcher(
        [
            PrintHook(),
            BusHook(event_bus, shard_id=wf_exec.shard_id),
            DBHook(
                exec_svc,
                WorkflowEventService(WorkflowEventRepository(session)),
                WorkflowVisibilityService(WorkflowVisibilityRepository(session)),
            ),
        ]
    )

    # ─────────────────────────────────────────────────────────────────────
    # 完成 _build_engine 后续辅助方法
    # ─────────────────────────────────────────────────────────────────────

    engine = WorkflowEngine(
        hook=hook,
        execution_service=exec_svc,
        task_service=ActivityTaskService(ActivityTaskRepository(session)),
        timer_service=TimerService(TimerRepository(session)),
        mode=mode,
    )
    engine.initialize(run_id, dsl, ctx, current_state=wf_exec.current_state_name)
    return engine, ctx


# =======================================================================
#                    public helper runners
# =======================================================================

async def advance_workflow(run_id: str) -> Dict[str, Any]:
    """
    deferred 模式推进一次（由 Worker/CLI 调用）。
    返回结果同 advance_once。
    """
    async with AsyncSessionLocal() as session:
        try:
            engine, _ = await _build_engine(session, run_id, mode="deferred")
            while True:
                res = await engine.advance_once()
                if not res["should_continue"]:
                    return res
        except Exception as exc:
            logger.exception("[%s] advance_workflow error: %s", run_id, exc)
            exec_svc = WorkflowExecutionService(WorkflowExecutionRepository(session))
            await exec_svc.fail_workflow(run_id, {"error": str(exc)})
            return {"status": "error", "context": str(exc)}


async def run_inline_workflow(run_id: str) -> Dict[str, Any]:
    """
    inline 模式：同步执行到终态（测试 / CLI 调用）。
    """
    async with AsyncSessionLocal() as session:
        try:
            engine, ctx = await _build_engine(session, run_id, mode="inline")
            result = await engine.run(run_id, engine.dsl, ctx)  # type: ignore[arg-type]
            return {"status": "finished", "result": result}
        except Exception as exc:
            logger.exception("[%s] inline run error: %s", run_id, exc)
            exec_svc = WorkflowExecutionService(WorkflowExecutionRepository(session))
            await exec_svc.fail_workflow(run_id, {"error": str(exc)})
            return {"status": "error", "result": str(exc)}