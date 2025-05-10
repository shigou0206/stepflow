
import asyncio
from datetime import datetime
from stepflow.events.in_memory_eventbus import InMemoryEventBus
from stepflow.hooks.event_hooks import EventHookExecutor
from stepflow.events.eventbus_model import EventType, EventEnvelope
from stepflow.hooks.base import WorkflowControlType


async def test_hooks():
    run_id = "run-001"
    state_id = "StepA"

    # 1. 初始化内存事件总线与 hook
    bus = InMemoryEventBus()
    hook = EventHookExecutor(event_bus=bus, shard_id=0)

    # 2. 收集事件结果
    events = []

    def log_event(evt: EventEnvelope):
        print(f"[EVENT] {evt.event_type} - {evt.state_id or 'workflow'}")
        events.append(evt)

    for et in EventType:
        bus.subscribe(et, log_event)

    # 3. 启动事件分发循环
    dispatcher = asyncio.create_task(bus.start_dispatch_loop())

    # 4. 模拟工作流执行各阶段
    await hook.on_workflow_start(run_id)
    await hook.on_node_enter(run_id, state_id, {"x": 1})
    await hook.on_node_success(run_id, state_id, {"y": 99})
    await hook.on_control_signal(run_id, WorkflowControlType.Cancel, "User requested")
    await hook.on_workflow_end(run_id, "Canceled")

    # 5. 等待事件进入事件处理器（最多等待 1s）
    for _ in range(10):
        if len(events) >= 5:
            break
        await asyncio.sleep(0.1)

    dispatcher.cancel()

    # 6. 断言检查（用于单元测试场景）
    assert len(events) >= 5, f"Expected 5 events, got {len(events)}"
    assert events[0].event_type == EventType.WorkflowStart
    assert events[1].event_type == EventType.NodeEnter
    assert events[2].event_type == EventType.NodeSuccess
    assert events[2].attributes["output"]["y"] == 99
    assert events[3].event_type == EventType.WorkflowControl
    assert events[4].event_type == EventType.WorkflowEnd

    print("\n✅ All hook events triggered and verified.")


if __name__ == "__main__":
    asyncio.run(test_hooks())
