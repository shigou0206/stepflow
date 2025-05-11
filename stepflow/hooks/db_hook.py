import json
import logging
import traceback
from datetime import datetime, UTC
from typing import Any, Dict

from stepflow.events.eventbus_model import EventType
from stepflow.hooks.base import ExecutionHooks
from stepflow.service.workflow_event_service import WorkflowEventService
from stepflow.service.workflow_execution_service import WorkflowExecutionService
from stepflow.service.workflow_visibility_service import WorkflowVisibilityService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DBHook(ExecutionHooks):
    def __init__(
        self,
        execution_service: WorkflowExecutionService,
        event_service: WorkflowEventService,
        visibility_service: WorkflowVisibilityService,
        shard_id: int = 1,
    ):
        self.exec_service = execution_service
        self.event_service = event_service
        self.vis_service = visibility_service
        self.shard_id = shard_id

    async def _record_event(self, run_id: str, event_type: EventType, **attrs):
        try:
            event_id = await self.exec_service.next_event_id(run_id)
            await self.event_service.record_event(
                run_id=run_id,
                shard_id=self.shard_id,
                event_id=event_id,
                event_type=event_type.value,  # 确保为字符串
                attributes=json.dumps(attrs, ensure_ascii=False),
            )
        except Exception as e:
            logger.exception(f"[DBHook] ❌ Failed to record event {event_type.name} for {run_id}: {e}")

    async def on_workflow_start(self, run_id: str):
        await self._record_event(
            run_id,
            EventType.WorkflowStart,
            timestamp=datetime.now(UTC).isoformat()
        )

    async def on_node_enter(self, run_id: str, state_id: str, input_data: Any):
        await self._record_event(
            run_id,
            EventType.NodeEnter,
            state_id=state_id,
            input=input_data
        )

    async def on_node_success(self, run_id: str, state_id: str, output_data: Any):
        await self._record_event(
            run_id,
            EventType.NodeSuccess,
            state_id=state_id,
            output=output_data
        )

    async def on_node_fail(self, run_id: str, state_id: str, error_msg: str):
        await self._record_event(
            run_id,
            EventType.NodeFail,
            state_id=state_id,
            error=error_msg,
            trace=traceback.format_exc()
        )

    async def on_node_dispatch(self, run_id: str, state_id: str, input_data: Any):
        await self._record_event(
            run_id,
            EventType.NodeDispatch,
            state_id=state_id,
            input=input_data
        )

    async def on_workflow_end(self, run_id: str, result: Any):
        await self._record_event(
            run_id,
            EventType.WorkflowEnd,
            result=result
        )
        try:
            # 如果当前状态已经是终止态，就跳过更新
            exec_obj = await self.exec_service.get_execution(run_id)
            if exec_obj.status not in {"completed", "failed", "canceled"}:
                await self.exec_service.complete_workflow(run_id, result=result)
                await self.vis_service.update_visibility_status(run_id, "completed")
            else:
                logger.info(f"[DBHook] Workflow {run_id} already {exec_obj.status}, skip mark completed.")
        except Exception as e:
            logger.exception(f"[DBHook] Failed to mark workflow {run_id} as completed: {e}")

    async def on_control_signal(self, run_id: str, signal_type: str, reason: str):
        await self._record_event(
            run_id,
            EventType.WorkflowControl,
            signal=signal_type,
            reason=reason
        )
        if signal_type == "Cancel":
            try:
                await self.exec_service.cancel_workflow(run_id, result={"reason": reason})
                await self.vis_service.update_visibility_status(run_id, "canceled")
            except Exception as e:
                logger.exception(f"[DBHook] ❌ Failed to cancel workflow {run_id}: {e}")