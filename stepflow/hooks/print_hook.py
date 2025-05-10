import json
from typing import Any
from stepflow.hooks.base import ExecutionHooks

class PrintHook(ExecutionHooks):
    async def on_workflow_start(self, run_id: str):
        print(f"[{run_id}] 🚀 Workflow started")

    async def on_node_enter(self, run_id: str, state_name: str, input: Any):
        print(f"[{run_id}] ▶️ Entering {state_name} with input: {json.dumps(input, ensure_ascii=False)}")

    async def on_node_success(self, run_id: str, state_name: str, output: Any):
        print(f"[{run_id}] ✅ {state_name} succeeded, output: {json.dumps(output, ensure_ascii=False)}")

    async def on_node_fail(self, run_id: str, state_name: str, error: str):
        print(f"[{run_id}] ❌ {state_name} failed with error: {error}")

    async def on_workflow_end(self, run_id: str, result: Any):
        print(f"[{run_id}] 🏁 Workflow ended with result: {json.dumps(result, ensure_ascii=False)}")

    async def on_control_signal(self, run_id: str, signal_type: str, reason: str):
        print(f"[{run_id}] ⚠️ Control signal received: {signal_type} - Reason: {reason}")