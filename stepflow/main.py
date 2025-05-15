from __future__ import annotations

"""FastAPI entrypoint with ActivityWorker + TimerWorker support."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from stepflow.config import ENABLE_PROMETHEUS, ENABLE_OTEL
from stepflow.observability.prometheus_metrics import router as metrics_router
from stepflow.observability.otel_tracing import init_tracer

# ──────────────────────── routers ─────────────────────────
from stepflow.interfaces.api.workflow_visibility_endpoints import router as vis_router
from stepflow.interfaces.api.workflow_execution_endpoints import router as exec_router
from stepflow.interfaces.api.workflow_template_endpoints import router as template_router
from stepflow.interfaces.api.workflow_event_endpoints import router as event_router
from stepflow.interfaces.api.activity_endpoints import router as activity_router
from stepflow.interfaces.api.timer_endpoints import router as timer_router
from stepflow.interfaces.websocket.routes import router as websocket_router

# workers
from stepflow.worker.activity_worker import run_activity_worker
from stepflow.worker.timer_worker import run_timer_loop

# ──────────────────────── logging ──────────────────────────
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.basicConfig(
    level=logging.INFO,                      # ← 必须 DEBUG
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────── worker config ─────────────────────
NUM_ACTIVITY_WORKERS = int(os.getenv("NUM_ACTIVITY_WORKERS", "2"))
NUM_TIMER_WORKERS = int(os.getenv("NUM_TIMER_WORKERS", "1"))
TIMER_POLL_INTERVAL = float(os.getenv("TIMER_POLL_INTERVAL", "1.0"))

# ─────────────────── lifespan context manager ──────────────

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[valid-type]
    """Init DB, start workers on startup; cancel on shutdown."""

    # 1️⃣ 创建数据库 schema（仅首次）
    from stepflow.persistence.database import Base, async_engine

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2️⃣ 启动后台 worker
    workers: list[asyncio.Task] = []

    # Activity workers
    for _ in range(NUM_ACTIVITY_WORKERS):
        workers.append(asyncio.create_task(run_activity_worker()))
    logger.info("ActivityWorkers started: %s", NUM_ACTIVITY_WORKERS)

    # Timer workers (each runs its own poll loop; shard_id = idx)
    for idx in range(NUM_TIMER_WORKERS):
        task = asyncio.create_task(
            run_timer_loop(interval_seconds=TIMER_POLL_INTERVAL, shard_id=idx)
        )
        workers.append(task)
    logger.info("TimerWorkers started: %s", NUM_TIMER_WORKERS)

    app.state.workers = workers  # type: ignore[attr-defined]
    try:
        yield
    finally:
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        logger.info("All workers shut down.")

# ───────────────────────── FastAPI app ─────────────────────

app = FastAPI(title="StepFlow API", description="Workflow engine API", lifespan=lifespan)

# Prometheus / OTEL 初始化
if ENABLE_OTEL:
    init_tracer("stepflow")

if ENABLE_PROMETHEUS:
    app.include_router(metrics_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(vis_router)
app.include_router(exec_router)
app.include_router(template_router)
app.include_router(event_router)
app.include_router(activity_router)
app.include_router(timer_router)
app.include_router(websocket_router)


@app.get("/")
async def root():  # pragma: no cover
    return {"message": "StepFlow API is running"}


# ─────────────────────────── run uvicorn ────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
