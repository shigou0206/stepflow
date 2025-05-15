import os
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    multiprocess,
)

# ────────────────── Registry 处理 ─────────────────────────
if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
    _REGISTRY: CollectorRegistry | None = CollectorRegistry()
    multiprocess.MultiProcessCollector(_REGISTRY)
else:
    _REGISTRY = None  # 默认 registry

# ────────────────── Metric definitions ────────────────────
TASK_RESULTS = Counter(
    "activity_tasks_total",
    "Activity tasks processed by worker",
    ["activity_type", "status"],
    registry=_REGISTRY,
)

# 动态 buckets：确保覆盖 TASK_TIMEOUT_SECONDS
_TIMEOUT = int(os.getenv("TASK_TIMEOUT_SECONDS", "30"))
_DEFAULT_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10)
_BUCKETS = (*_DEFAULT_BUCKETS, _TIMEOUT if _TIMEOUT > 10 else 10, _TIMEOUT * 3)

TASK_DURATION = Histogram(
    "activity_task_duration_seconds",
    "Execution time of activity tasks",
    ["activity_type"],
    buckets=_BUCKETS,
    registry=_REGISTRY,
)

TASK_RUNNING = Gauge(
    "activity_tasks_running",
    "Number of tasks currently being executed",
    registry=_REGISTRY,
)

__all__ = [
    "TASK_RESULTS",
    "TASK_DURATION",
    "TASK_RUNNING",
    "_REGISTRY",
]