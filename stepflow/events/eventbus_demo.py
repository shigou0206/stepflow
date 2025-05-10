import asyncio
from datetime import datetime, UTC
from stepflow.events.eventbus_model import EventType, EventEnvelope
from stepflow.events.eventbus_factory import EventBusFactory


async def main():
    # 默认使用内存总线（可改为 "persistent" 并传入 db_session）
    bus = EventBusFactory.create("memory")
    await bus.start()

    def log_event(evt: EventEnvelope):
        print(f"[EVENT] {evt.event_type} @ {evt.timestamp} → {evt.attributes}")

    bus.subscribe(EventType.NodeEnter, log_event)
    bus.subscribe(EventType.NodeSuccess, log_event)

    # 构造测试事件
    await bus.publish(EventEnvelope(
        run_id="demo-run",
        shard_id=0,
        event_id=1,
        event_type=EventType.NodeEnter,
        timestamp=datetime.now(UTC),
        state_id="StepA",
        state_type="Task",
        attributes={"input": {"x": 1}}
    ))

    await bus.publish(EventEnvelope(
        run_id="demo-run",
        shard_id=0,
        event_id=2,
        event_type=EventType.NodeSuccess,
        timestamp=datetime.now(UTC),
        state_id="StepA",
        state_type="Task",
        attributes={"output": {"y": 99}}
    ))

    await asyncio.sleep(0.2)
    await bus.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
