import asyncio
import json
import logging
import traceback
import os
from datetime import datetime, UTC
from typing import List

from prometheus_client import Counter, start_http_server

from stepflow.persistence.database import AsyncSessionLocal
from stepflow.persistence.models import ActivityTask
from stepflow.persistence.repositories.activity_task_repository import ActivityTaskRepository
from stepflow.service.activity_task_service import ActivityTaskService
from stepflow.engine.workflow_engine import advance_workflow
from stepflow.worker.tools.tool_registry import tool_registry

# Prometheus metrics
TASKS_PROCESSED = Counter("activity_tasks_processed_total", "Total tasks processed")
TASKS_FAILED = Counter("activity_tasks_failed_total", "Total tasks failed")
TASKS_TIMEOUT = Counter("activity_tasks_timeout_total", "Total tasks timed out")

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Config from env
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "10"))
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "30"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "8001"))


async def run_activity_worker(poll_interval: int = 5):
    logger.info(f"🎯 ActivityWorker started, max concurrency: {MAX_CONCURRENT_TASKS}")
    start_http_server(METRICS_PORT)

    while True:
        try:
            await _process_available_tasks()
        except Exception as e:
            logger.exception(f"🔥 Worker loop error: {e}")

        await asyncio.sleep(poll_interval)


async def _process_available_tasks():
    async with AsyncSessionLocal() as session:
        repo = ActivityTaskRepository(session)
        service = ActivityTaskService(repo)

        # ✅ 使用 service 方法而非 repo
        tasks = await service.get_scheduled_tasks(limit=MAX_CONCURRENT_TASKS)
        if not tasks:
            return

        logger.info(f"📦 Found {len(tasks)} scheduled tasks")
        await service.mark_tasks_as_running(tasks)

        coros = [process_single_task(task, service) for task in tasks]
        await asyncio.gather(*coros, return_exceptions=False)


async def process_single_task(task: ActivityTask, service: ActivityTaskService):
    context = f"[task_token={task.task_token}] [run_id={task.run_id}]"
    logger.info(f"{context} 🚧 Executing task ({task.activity_type})")

    try:
        await service.start_task(task.task_token)

        tool = tool_registry.get(task.activity_type)
        if not tool:
            raise ValueError(f"Unknown tool type: {task.activity_type}")

        input_data = json.loads(task.input or "{}")

        try:
            result = await asyncio.wait_for(tool.execute(input_data), timeout=TASK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            TASKS_TIMEOUT.inc()
            raise TimeoutError(f"Tool execution timeout after {TASK_TIMEOUT_SECONDS}s")

        if isinstance(result, dict) and result.get("error"):
            await service.fail_task(
                task_token=task.task_token,
                reason=result.get("error"),
                details=result.get("error_details", "")
            )
            TASKS_FAILED.inc()
        else:
            result_data = result if isinstance(result, dict) else {"result": result}
            await service.complete_task(task.task_token, json.dumps(result_data))
            TASKS_PROCESSED.inc()

    except Exception as e:
        logger.exception(f"{context} ❌ Task failed: {e}")
        await service.fail_task(
            task_token=task.task_token,
            reason=str(e),
            details=traceback.format_exc()
        )
        TASKS_FAILED.inc()

    try:
        await advance_workflow(task.run_id)
    except Exception as e:
        logger.exception(f"{context} ⛔ Workflow advance failed: {e}")