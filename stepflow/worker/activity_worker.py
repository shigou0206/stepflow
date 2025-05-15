from __future__ import annotations

"""Activity Worker with metrics (multiprocess & robust)."""

import asyncio
import json
import logging
import os
import time
import traceback

from prometheus_client import start_http_server

from stepflow.persistence.database import AsyncSessionLocal
from stepflow.persistence.models import ActivityTask
from stepflow.persistence.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.service.activity_task_service import ActivityTaskService
from stepflow.engine.workflow_engine import advance_workflow
from stepflow.worker.tools.tool_registry import tool_registry

from stepflow.observability.prometheus_metrics_worker import (
    TASK_RESULTS,
    TASK_DURATION,
    TASK_RUNNING,
    _REGISTRY,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# ───── Config ─────────────────────────────────────────────
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "30"))
METRICS_PORT_BASE = int(os.getenv("METRICS_PORT", "8001"))
SHARD_ID = int(os.getenv("WORKER_SHARD_ID", "0"))


async def run_activity_worker(poll_interval: int = 5):
    """Main loop for ActivityWorker."""
    logger.info(
        "🎯 ActivityWorker[%s] started, max concurrency: %s", SHARD_ID, MAX_CONCURRENT_TASKS
    )

    # Metrics exposure strategy
    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        # multiprocess mode: metrics exposed by main process, workers无需 start_http_server
        logger.info("Using Prometheus multiprocess – metrics handled by main process")
    else:
        port = METRICS_PORT_BASE + SHARD_ID
        start_http_server(port, registry=_REGISTRY)
        logger.info("Metrics HTTP server on :%s", port)

    while True:
        try:
            await _process_available_tasks()
        except Exception as exc:  # noqa: BLE001
            logger.exception("🔥 Worker loop error: %s", exc)
        await asyncio.sleep(poll_interval)


async def _process_available_tasks() -> None:
    async with AsyncSessionLocal() as session:
        repo = ActivityTaskRepository(session)
        service = ActivityTaskService(repo)

        tasks = await service.get_scheduled_tasks(limit=MAX_CONCURRENT_TASKS)
        if not tasks:
            return

        logger.info("📦 Found %s scheduled tasks", len(tasks))
        await service.mark_tasks_as_running(tasks)

        await asyncio.gather(*(process_single_task(t, service) for t in tasks))


async def process_single_task(task: ActivityTask, service: ActivityTaskService) -> None:  # noqa: C901 (complexity ok)
    ctx = f"[task_token={task.task_token}] [run_id={task.run_id}]"
    logger.info("%s 🚧 Executing task (%s)", ctx, task.activity_type)

    TASK_RUNNING.inc()  # gauge +1

    status_label = "success"
    duration_start = time.perf_counter()

    try:
        await service.start_task(task.task_token)

        tool = tool_registry.get(task.activity_type)
        if tool is None:
            status_label = "fail"
            raise ValueError(f"Unknown tool type: {task.activity_type}")

        input_data = json.loads(task.input or "{}")

        try:
            result = await asyncio.wait_for(tool.execute(input_data), timeout=TASK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:  # execution timeout
            status_label = "timeout"
            raise TimeoutError(f"Timeout after {TASK_TIMEOUT_SECONDS}s")

        # success path or business failure
        if isinstance(result, dict) and result.get("error"):
            status_label = "fail"
            await service.fail_task(
                task_token=task.task_token, reason=result["error"], details=result.get("error_details", "")
            )
        else:
            out = result if isinstance(result, dict) else {"result": result}
            await service.complete_task(task.task_token, json.dumps(out))

    except Exception as exc:  # noqa: BLE001
        logger.exception("%s ❌ Task error: %s", ctx, exc)
        if status_label != "timeout":
            status_label = "fail"
        # Mark DB fail (ignore errors in DB update)
        try:
            await service.fail_task(
                task_token=task.task_token, reason=str(exc), details=traceback.format_exc()
            )
        except Exception:  # noqa: BLE001
            pass
    finally:
        # 计时 & Counter 统一在 finally 保证一定执行
        elapsed = time.perf_counter() - duration_start
        TASK_DURATION.labels(task.activity_type).observe(elapsed)
        TASK_RESULTS.labels(task.activity_type, status_label).inc()
        TASK_RUNNING.dec()

        try:
            await advance_workflow(task.run_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s ⛔ advance_workflow failed: %s", ctx, exc)