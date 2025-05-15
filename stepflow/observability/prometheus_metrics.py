"""
Prometheus metric definitions  +  /metrics route (multiprocess-ready)
--------------------------------------------------------------------
• 若设置环境变量  PROMETHEUS_MULTIPROC_DIR=<dir>：
    - 使用 multiprocess Collector 聚合所有进程写入的 .db 文件
    - Worker 只需写文件，不必开端口
• 否则回退为单进程默认注册表
"""

import os

from fastapi import APIRouter, Response
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CollectorRegistry,
    multiprocess,
)

from stepflow.config import ENABLE_PROMETHEUS

router = APIRouter()

# ────────── Registry 处理 ───────────────────────────────────
if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
    _REGISTRY: CollectorRegistry | None = CollectorRegistry()
    multiprocess.MultiProcessCollector(_REGISTRY)
else:
    _REGISTRY = None  # 使用默认全局 registry
# ───────────────────────────────────────────────────────────

# ────────── Metric definitions ─────────────────────────────
workflow_started = Counter(
    "workflow_started_total",
    "Total workflows started in StepFlow",
    registry=_REGISTRY,
)

node_success = Counter(
    "node_success_total",
    "Successful node executions",
    ["state_id"],
    registry=_REGISTRY,
)

node_fail = Counter(
    "node_fail_total",
    "Failed node executions",
    ["state_id"],
    registry=_REGISTRY,
)

node_duration = Histogram(
    "node_duration_seconds",
    "Node execution duration (seconds)",
    ["state_id"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    registry=_REGISTRY,
)
# ───────────────────────────────────────────────────────────

# ────────── /metrics endpoint ──────────────────────────────
if ENABLE_PROMETHEUS:
    @router.get("/metrics")
    def metrics() -> Response:            # pragma: no cover
        """Prometheus scrape endpoint."""
        return Response(
            generate_latest(_REGISTRY),
            media_type="text/plain",
        )