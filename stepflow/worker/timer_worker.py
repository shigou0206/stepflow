# stepflow/worker/timer_worker.py

import asyncio
from datetime import datetime, timezone
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.application.timer_service import TimerService
from stepflow.infrastructure.repositories.timer_repository import TimerRepository
from stepflow.domain.engine.execution_engine import advance_workflow

CHECK_INTERVAL = 5  # 每5秒轮询一次(示例)

async def run_timer_worker():
    """
    后台协程, 轮询 "timers" 表, 查找 fire_at <= now() 且 status='scheduled'
    然后标记fired, 并可调用Engine/Workflow推进
    """
    while True:

        # 2) 获取当前UTC时间(也可用 localtime,视你DB存储)
        now_utc = datetime.now(timezone.utc)

        # 3) 打开异步Session:
        async with AsyncSessionLocal() as db:
            repo = TimerRepository(db)
            svc = TimerService(repo)

            # 4) 查找 scheduled & fire_at <= now()
            due_list = await svc.find_due_timers(now_utc)
            if due_list:
                print(f"[TimerWorker] found {len(due_list)} timers due.")
            
            # 5) 对于每个到期的Timer:
            for t in due_list:
                # a) fire它 => status='fired'
                fired_ok = await svc.fire_timer(t.timer_id)
                if fired_ok:
                    print(f"[TimerWorker] Timer {t.timer_id} -> fired. run_id={t.run_id}")

                    # b) 通知引擎:
                    #    (如果你的引擎用 DSL WaitState => you'd do something like:
                    #     advance_workflow(db, t.run_id, event="TimerFired")
                    #     or a simpler approach: just run full advance_workflow)
                    #    下面是示例:
                    await advance_workflow(db, t.run_id)

                # c) 如果需要send websocket / event bus，也可在这里做
                # e.g. broadcast_workflow_event( {"event":"TimerFired", "timer_id":..., ...} )

        # 6) 休眠
        await asyncio.sleep(CHECK_INTERVAL)