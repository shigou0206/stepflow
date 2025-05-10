from typing import List
from stepflow.hooks.base import ExecutionHooks

class HookDispatcher(ExecutionHooks):
    def __init__(self, hooks: List[ExecutionHooks]):
        self.hooks = hooks

    async def on_workflow_start(self, run_id):
        for h in self.hooks:
            await h.on_workflow_start(run_id)

    async def on_node_enter(self, run_id, state_name, input):
        for h in self.hooks:
            await h.on_node_enter(run_id, state_name, input)

    async def on_node_success(self, run_id, state_name, output):
        for h in self.hooks:
            await h.on_node_success(run_id, state_name, output)

    async def on_node_fail(self, run_id, state_name, error):
        for h in self.hooks:
            await h.on_node_fail(run_id, state_name, error)

    async def on_workflow_end(self, run_id, result):
        for h in self.hooks:
            await h.on_workflow_end(run_id, result)

    async def on_control_signal(self, run_id, signal_type, reason):
        for h in self.hooks:
            await h.on_control_signal(run_id, signal_type, reason)