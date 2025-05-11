import pytest
import asyncio
from stepflow.hooks.bus_hook import BusHook
from stepflow.events.in_memory_eventbus import InMemoryEventBus
from stepflow.events.eventbus_model import EventType


@pytest.mark.asyncio
async def test_bus_hook_event_emission():
    run_id = "test-run-001"
    state_id = "StateA"
    input_data = {"foo": 1}
    output_data = {"bar": 2}
    error_msg = "Something failed"
    reason = "cancelled by user"

    event_log = []

    bus = InMemoryEventBus()
    for et in EventType:
        bus.subscribe(et, lambda e, et=et: event_log.append(e))  # ✅ 闭包安全

    hook = BusHook(bus=bus, shard_id=1)
    await bus.start()

    try:
        await hook.on_workflow_start(run_id)
        await hook.on_node_enter(run_id, state_id, input_data)
        await hook.on_node_success(run_id, state_id, output_data)
        await hook.on_node_fail(run_id, state_id, error_msg)
        await hook.on_node_dispatch(run_id, state_id, input_data)
        await hook.on_control_signal(run_id, "cancel", reason)
        await hook.on_workflow_end(run_id, {"status": "ok"})

        await bus.event_queue.join()

        assert len(event_log) == 7
        types = [e.event_type for e in event_log]
        assert types == [
            EventType.WorkflowStart,
            EventType.NodeEnter,
            EventType.NodeSuccess,
            EventType.NodeFail,
            EventType.NodeDispatch,
            EventType.WorkflowControl,
            EventType.WorkflowEnd,
        ]

        assert event_log[1].attributes["input"] == input_data
        assert event_log[2].attributes["output"] == output_data
        assert event_log[3].attributes["error"] == error_msg
        assert event_log[5].attributes["signal"] == "cancel"
    finally:
        await bus.shutdown()


@pytest.mark.asyncio
async def test_bus_hook_multiple_subscribers_receive_event():
    run_id = "test-run-001"
    state_id = "StateX"
    input_data = {"foo": 42}

    bus = InMemoryEventBus()
    hook = BusHook(bus=bus, shard_id=1)

    received_1 = []
    received_2 = []

    bus.subscribe(EventType.NodeEnter, lambda e: received_1.append(e))
    bus.subscribe(EventType.NodeEnter, lambda e: received_2.append(e))

    await bus.start()
    try:
        await hook.on_node_enter(run_id, state_id, input_data)
        await bus.event_queue.join()

        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0].attributes["input"] == input_data
        assert received_2[0].attributes["input"] == input_data
    finally:
        await bus.shutdown()


@pytest.mark.asyncio
async def test_bus_hook_subscriber_exception_isolated():
    run_id = "test-run-iso"
    state_id = "StateY"
    input_data = {"x": 123}

    bus = InMemoryEventBus()
    hook = BusHook(bus, shard_id=2)

    ok_log = []

    def good_handler(evt):
        ok_log.append(evt)

    def bad_handler(evt):
        raise RuntimeError("simulated failure")

    bus.subscribe(EventType.NodeEnter, bad_handler)
    bus.subscribe(EventType.NodeEnter, good_handler)

    await bus.start()
    try:
        await hook.on_node_enter(run_id, state_id, input_data)
        await bus.event_queue.join()

        assert len(ok_log) == 1
        assert ok_log[0].attributes["input"] == input_data
    finally:
        await bus.shutdown()


@pytest.mark.asyncio
async def test_event_id_isolated_per_run():
    run_ids = ["run-A", "run-B", "run-C"]
    event_log = []

    bus = InMemoryEventBus()
    bus.subscribe(EventType.WorkflowStart, lambda e: event_log.append((e.run_id, e.event_id)))

    hook = BusHook(bus, shard_id=0)
    await bus.start()
    try:
        for rid in run_ids:
            await hook.on_workflow_start(rid)

        await bus.event_queue.join()
        assert sorted(event_log) == [(rid, 1) for rid in run_ids]
    finally:
        await bus.shutdown()

@pytest.mark.asyncio
async def test_event_id_isolated_per_run():
    hook = BusHook(bus=InMemoryEventBus(), shard_id=0)
    await hook.on_workflow_start("run-001")
    await hook.on_workflow_start("run-002")
    await hook.on_workflow_start("run-001")
    assert hook._event_id_counter["run-001"] == 2
    assert hook._event_id_counter["run-002"] == 1


@pytest.mark.asyncio
async def test_async_handler_execution():
    bus = InMemoryEventBus()
    called = []

    async def async_handler(event):  # async 版本
        called.append(event)

    bus.subscribe(EventType.WorkflowStart, async_handler)
    hook = BusHook(bus, shard_id=1)
    await bus.start()
    try:
        await hook.on_workflow_start("run-100")
        await bus.event_queue.join()
        assert len(called) == 1
    finally:
        await bus.shutdown()


@pytest.mark.asyncio
async def test_event_with_no_subscribers_is_safe():
    bus = InMemoryEventBus()
    hook = BusHook(bus, shard_id=0)
    await bus.start()
    try:
        # 没有订阅 WorkflowFail，但也不能报错或卡死
        await hook.on_workflow_end("run-x", {"status": "test"})
        await bus.event_queue.join()
    finally:
        await bus.shutdown()


@pytest.mark.asyncio
async def test_dispatcher_multiple_start_does_not_duplicate():
    bus = InMemoryEventBus()
    await bus.start()
    first = bus.dispatcher
    await bus.start()
    second = bus.dispatcher
    assert first is second
    await bus.shutdown()


@pytest.mark.asyncio
async def test_shutdown_waits_for_unconsumed_events():
    bus = InMemoryEventBus()
    hook = BusHook(bus, shard_id=0)

    called = []

    async def handler(event):
        await asyncio.sleep(0.1)
        called.append(event)

    bus.subscribe(EventType.WorkflowStart, handler)

    await bus.start()
    await hook.on_workflow_start("run-block")
    await bus.shutdown()

    assert len(called) == 1


@pytest.mark.asyncio
async def test_subscribe_all_events_simulated():
    bus = InMemoryEventBus()
    seen = []

    def catch_all(event):
        seen.append(event.event_type)

    for et in EventType:
        bus.subscribe(et, catch_all)

    hook = BusHook(bus, shard_id=0)
    await bus.start()
    await hook.on_workflow_start("run-001")
    await hook.on_workflow_end("run-001", {"done": True})
    await bus.event_queue.join()
    await bus.shutdown()

    assert EventType.WorkflowStart in seen
    assert EventType.WorkflowEnd in seen