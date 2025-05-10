import logging
from typing import Dict, Any, Optional
from stepflow.dsl.dsl_model import WorkflowDSL
from stepflow.engine.step_runner import step_once
from stepflow.hooks.base import ExecutionHooks
from stepflow.worker.task_executor import TaskExecutor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WorkflowEngine:
    def __init__(self, hook: ExecutionHooks):
        self.hook = hook
        self.executor = TaskExecutor()
        self.dsl: Optional[WorkflowDSL] = None
        self.run_id: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.current_state: Optional[str] = None
        self.finished: bool = False
        self.result: Any = None

    def initialize(self, run_id: str, dsl: WorkflowDSL, input_data: Dict[str, Any]):
        self.dsl = dsl
        self.run_id = run_id
        self.context = input_data
        self.current_state = dsl.start_at
        self.finished = False
        self.result = None

    async def advance_once(self):
        print(f"[{self.run_id}] 🔄 advance_once → state: {self.current_state}")
        if self.finished or not self.current_state:
            return

        cmd = step_once(self.dsl, self.current_state, self.context)
        print(f"[{self.run_id}] Step → {cmd.type} : {cmd.state_name}")

        if cmd.type == "ExecuteTask":
            state = self.dsl.states[cmd.state_name]
            await self.hook.on_node_enter(self.run_id, cmd.state_name, self.context)
            try:
                result = await self.executor.run_task(state, self.context)
                await self.hook.on_node_success(self.run_id, cmd.state_name, result)
                self.context = result

                # ✅ 判断 End 是否为 True
                if getattr(state, "end", False):
                    await self.hook.on_workflow_end(self.run_id, result)
                    self.result = result
                    self.finished = True
                else:
                    self.current_state = cmd.next_state
            except Exception as e:
                await self.hook.on_node_fail(self.run_id, cmd.state_name, str(e))
                self.finished = True

        elif cmd.type == "Pass":
            self.context = cmd.output
            self.current_state = cmd.next_state

        elif cmd.type == "Succeed":
            await self.hook.on_workflow_end(self.run_id, cmd.output)
            self.result = cmd.output
            self.finished = True

        elif cmd.type == "Fail":
            await self.hook.on_workflow_end(self.run_id, f"Failed: {cmd.error}")
            self.result = {"error": cmd.error, "cause": cmd.cause}
            self.finished = True
        
        else:
            logger.error(f"Unknown command type: {cmd.type}, terminating.")
            self.finished = True

        print(f"[{self.run_id}] 🔚 post-step → state: {self.current_state}, finished: {self.finished}")

    async def run(self, run_id: str, dsl: WorkflowDSL, input_data: Dict[str, Any]):
        print(f"Start workflow {run_id}")
        await self.hook.on_workflow_start(run_id)
        self.initialize(run_id, dsl, input_data)

        while not self.finished and self.current_state is not None:
            await self.advance_once()

        print(f"[{run_id}] 🎯 Workflow finished. Result = {self.result}")
        assert self.finished, f"[{run_id}] ⚠️ run() exited but not marked as finished"

        return self.result