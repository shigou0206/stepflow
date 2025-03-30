# stepflow/worker/main_worker.py

import asyncio
from .activity_worker import run_activity_worker
# 如果有 TimerWorker, from .timer_worker import run_timer_worker

async def main_worker():
    # 如果你有多个 worker, 可以 gather
    workers = [
        asyncio.create_task(run_activity_worker()),
        # asyncio.create_task(run_timer_worker()),
    ]
    await asyncio.gather(*workers)

if __name__ == "__main__":
    asyncio.run(main_worker())