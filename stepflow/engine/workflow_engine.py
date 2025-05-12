import logging
import json
from typing import Dict, Any, Optional, Literal

from stepflow.dsl.dsl_model import WorkflowDSL
from stepflow.engine.step_runner import step_once
from stepflow.worker.task_executor import TaskExecutor

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

from stepflow.expression.parameter_mapper import (
    apply_parameters,
    apply_result_expr,
    apply_output_expr,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class WorkflowEngine:
    def __init__(
        self,
        hook: ExecutionHooks,
        execution_service: WorkflowExecutionService,
        task_service: ActivityTaskService,
        mode: Literal["inline", "deferred"] = "inline"
    ):
        self.hook = hook
        self.mode = mode
        self.executor = TaskExecutor()
        self.execution_service = execution_service
        self.task_service = task_service
        self.dsl: Optional[WorkflowDSL] = None
        self.run_id: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.current_state: Optional[str] = None
        self.finished: bool = False
        self.result: Any = None

    def initialize(self, run_id: str, dsl: WorkflowDSL, input_data: Dict[str, Any], current_state: Optional[str] = None):
        self.dsl = dsl
        self.run_id = run_id
        self.context = input_data
        self.current_state = current_state or dsl.start_at
        self.finished = False
        self.result = None

    async def advance_once(self) -> Dict[str, Any]:
        logger.info(f"[{self.run_id}] 🔄 advance_once → state: {self.current_state}")
        if self.finished or not self.current_state:
            return {"status": "finished", "should_continue": False, "context": self.context}

        try:
            await self.execution_service.update_current_state(self.run_id, self.current_state)
            cmd = step_once(self.dsl, self.current_state, self.context)
        except Exception as e:
            logger.exception(f"[{self.run_id}] ❌ step_once failed: {e}")
            error = {"error": str(e)}
            await self.execution_service.fail_workflow(self.run_id, error)
            await self.hook.on_workflow_end(self.run_id, error)
            self.result = error
            self.finished = True
            return {"status": "error", "should_continue": False, "context": error}

        logger.info(f"[{self.run_id}] Step → {cmd.type} : {cmd.state_name}")

        state = self.dsl.states[cmd.state_name]

        if cmd.type == "ExecuteTask":
            await self.hook.on_node_enter(self.run_id, cmd.state_name, self.context)

            if self.mode == "inline":
                data_input = apply_parameters(self.context, state.parameters, input_expr=state.input_expr)
                try:
                    result = await self.executor.run_task(state, data_input)
                    await self.hook.on_node_success(self.run_id, cmd.state_name, result)
                    intermediate = apply_result_expr(result, state.result_expr)
                    result = apply_output_expr(intermediate, state.output_expr)
                    self.context = result
                    await self.execution_service.update_context_snapshot(self.run_id, self.context)

                    if getattr(state, "end", False):
                        await self.execution_service.complete_workflow(self.run_id, result)
                        await self.hook.on_workflow_end(self.run_id, result)
                        self.result = result
                        self.finished = True
                        return {"status": "finished", "should_continue": False, "context": result}
                    else:
                        self.current_state = cmd.next_state
                        return {"status": "continue", "should_continue": True, "context": result}
                except Exception as e:
                    await self.hook.on_node_fail(self.run_id, cmd.state_name, str(e))
                    await self.execution_service.fail_workflow(self.run_id, {"error": str(e)})
                    self.result = {"error": str(e)}
                    self.finished = True
                    return {"status": "error", "should_continue": False, "context": self.context}

            elif self.mode == "deferred":
                task = await self.task_service.get_by_run_id_and_state(self.run_id, cmd.state_name)

                if not task:
                    data_input = apply_parameters(self.context, state.parameters, input_expr=state.input_expr)
                    logger.info(f"[{self.run_id}] 🚚 Task input = {json.dumps(data_input)}")
                    input_json = json.dumps(data_input)

                    await self.task_service.create_task(
                        run_id=self.run_id,
                        state_name=cmd.state_name,
                        activity_type=state.resource,
                        input_data=input_json
                    )
                    await self.hook.on_node_dispatch(self.run_id, cmd.state_name, self.context)
                    self.finished = True
                    return {"status": "paused", "should_continue": False, "context": self.context}

                if task.status == "failed":
                    error = {"error": task.error, "details": task.error_details}
                    await self.execution_service.fail_workflow(self.run_id, error)
                    await self.hook.on_workflow_end(self.run_id, error)
                    self.result = error
                    self.finished = True
                    return {"status": "error", "should_continue": False, "context": error}

                if task.status != "completed":
                    logger.info(f"[{self.run_id}] ⏸️ Waiting for task '{cmd.state_name}' to complete")
                    self.finished = True
                    return {"status": "paused", "should_continue": False, "context": self.context}

                try:
                    result_data = json.loads(task.result or "{}")
                except Exception:
                    result_data = {"result": task.result}

                await self.hook.on_node_success(self.run_id, cmd.state_name, result_data)

                intermediate = apply_result_expr(result_data, state.result_expr)
                output_data = apply_output_expr(intermediate, state.output_expr)
                self.context = output_data
                await self.execution_service.update_context_snapshot(self.run_id, self.context)

                if getattr(state, "end", False):
                    await self.execution_service.complete_workflow(self.run_id, output_data)
                    await self.hook.on_workflow_end(self.run_id, output_data)
                    self.result = output_data
                    self.finished = True
                    return {"status": "finished", "should_continue": False, "context": output_data}
                else:
                    self.current_state = cmd.next_state
                    return {"status": "continue", "should_continue": True, "context": output_data}

        elif cmd.type == "Pass":
            self.context = cmd.output
            self.current_state = cmd.next_state
            await self.execution_service.update_context_snapshot(self.run_id, self.context)
            return {"status": "continue", "should_continue": True, "context": self.context}

        elif cmd.type == "Choice":
            self.current_state = cmd.next_state
            return {"status": "continue", "should_continue": True, "context": self.context}

        elif cmd.type == "Succeed":
            await self.execution_service.complete_workflow(self.run_id, cmd.output)
            await self.hook.on_workflow_end(self.run_id, cmd.output)
            self.result = cmd.output
            self.finished = True
            return {"status": "finished", "should_continue": False, "context": cmd.output}

        elif cmd.type == "Fail":
            self.result = {"error": cmd.error, "cause": cmd.cause}
            await self.execution_service.fail_workflow(self.run_id, self.result)
            await self.hook.on_workflow_end(self.run_id, self.result)
            self.finished = True
            return {"status": "error", "should_continue": False, "context": self.result}

        else:
            logger.error(f"Unknown command type: {cmd.type}, terminating.")
            self.finished = True
            return {"status": "unknown", "should_continue": False, "context": self.context}


async def advance_workflow(run_id: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        exec_service = WorkflowExecutionService(WorkflowExecutionRepository(session))
        wf_exec = await exec_service.get_execution(run_id)
        if not wf_exec:
            raise ValueError(f"Workflow execution {run_id} not found")

        if wf_exec.status in {"failed", "completed"}:
            logger.warning(f"[{run_id}] 🚫 Cannot advance, already terminal: {wf_exec.status}")
            return {"status": wf_exec.status}

        tmpl_service = WorkflowTemplateService(WorkflowTemplateRepository(session))
        tmpl = await tmpl_service.get_template(wf_exec.template_id)
        if not tmpl:
            raise ValueError(f"Template {wf_exec.template_id} not found")

        dsl = parse_dsl_model(json.loads(tmpl.dsl_definition))
        context = json.loads(wf_exec.context_snapshot or wf_exec.result or wf_exec.input or "{}")

        event_bus = InMemoryEventBus()
        event_service = WorkflowEventService(WorkflowEventRepository(session))
        vis_service = WorkflowVisibilityService(WorkflowVisibilityRepository(session))
        task_service = ActivityTaskService(ActivityTaskRepository(session))
        hook = HookDispatcher([
            PrintHook(),
            BusHook(event_bus, shard_id=wf_exec.shard_id),
            DBHook(exec_service, event_service, vis_service, shard_id=wf_exec.shard_id)
        ])

        engine = WorkflowEngine(
            hook=hook,
            execution_service=exec_service,
            task_service=task_service,
            mode="deferred"
        )
        engine.initialize(run_id, dsl, context, current_state=wf_exec.current_state_name)

        try:
            while True:
                result = await engine.advance_once()
                if not result.get("should_continue", False):
                    return result
        except Exception as e:
            logger.exception(f"[{run_id}] ❌ Unhandled error in advance loop: {e}")
            error = {"error": str(e)}
            await exec_service.fail_workflow(run_id, error)
            return {"status": "error", "context": error}


async def run_inline_workflow(run_id: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        exec_service = WorkflowExecutionService(WorkflowExecutionRepository(session))
        wf_exec = await exec_service.get_execution(run_id)
        if not wf_exec:
            raise ValueError(f"Workflow execution {run_id} not found")

        if wf_exec.status in {"failed", "completed"}:
            logger.warning(f"[{run_id}] 🚫 Cannot run, already terminal: {wf_exec.status}")
            return {"status": wf_exec.status}

        tmpl_service = WorkflowTemplateService(WorkflowTemplateRepository(session))
        tmpl = await tmpl_service.get_template(wf_exec.template_id)
        if not tmpl:
            raise ValueError(f"Template {wf_exec.template_id} not found")

        dsl = parse_dsl_model(json.loads(tmpl.dsl_definition))
        context = json.loads(wf_exec.context_snapshot or wf_exec.result or wf_exec.input or "{}")

        event_bus = InMemoryEventBus()
        event_service = WorkflowEventService(WorkflowEventRepository(session))
        vis_service = WorkflowVisibilityService(WorkflowVisibilityRepository(session))
        task_service = ActivityTaskService(ActivityTaskRepository(session))
        hook = HookDispatcher([
            PrintHook(),
            BusHook(event_bus, shard_id=wf_exec.shard_id),
            DBHook(exec_service, event_service, vis_service, shard_id=wf_exec.shard_id)
        ])

        engine = WorkflowEngine(
            hook=hook,
            execution_service=exec_service,
            task_service=task_service,
            mode="inline"
        )
        engine.initialize(run_id, dsl, context, current_state=wf_exec.current_state_name)

        try:
            result = await engine.run(run_id, dsl, context)
            return {"status": "finished", "result": result}
        except Exception as e:
            logger.exception(f"[{run_id}] ❌ Inline workflow execution failed: {e}")
            error = {"error": str(e)}
            await exec_service.fail_workflow(run_id, error)
            return {"status": "error", "result": error}