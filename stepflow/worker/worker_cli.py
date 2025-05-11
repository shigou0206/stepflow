import os
import click
import asyncio

from stepflow.worker.activity_worker import (
    run_activity_worker,
    _process_available_tasks,
)

@click.command()
@click.option("--once", is_flag=True, help="Run only one fetch/execute cycle (for debugging).")
@click.option("--interval", default=5, help="Polling interval in seconds.")
@click.option("--concurrency", default=10, help="Max concurrent tasks to run.")
@click.option("--metrics-port", default=8001, help="Port to expose Prometheus metrics.")
@click.option("--timeout", default=30, help="Max execution timeout per task (in seconds).")
def cli(once, interval, concurrency, metrics_port, timeout):
    """
    Start the Activity Worker (with CLI options for interval, concurrency, timeout).
    """
    # 设置环境变量用于 worker 配置
    os.environ["MAX_CONCURRENT_TASKS"] = str(concurrency)
    os.environ["METRICS_PORT"] = str(metrics_port)
    os.environ["TASK_TIMEOUT_SECONDS"] = str(timeout)

    if once:
        asyncio.run(_process_available_tasks())
    else:
        asyncio.run(run_activity_worker(poll_interval=interval))


if __name__ == "__main__":
    cli()