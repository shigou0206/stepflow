from __future__ import annotations

"""Timer Worker with verbose debug logging."""

from asyncio import gather, sleep
from datetime import datetime, UTC
import logging
import sys
from typing import Awaitable, Callable, AsyncGenerator, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.engine.workflow_engine import advance_workflow
from stepflow.persistence.database import get_db_session
from stepflow.persistence.models import Timer
from stepflow.persistence.repositories.timer_repository import TimerRepository
from stepflow.service.timer_service import TimerService

# -----------------------------------------------------------------------------
# Logger setup
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handler if not already added
if not logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# -----------------------------------------------------------------------------
# Single-timer processing
# -----------------------------------------------------------------------------


async def process_single_timer(
    timer: Timer,
    svc: TimerService,
    *,
    now: datetime,
    max_retries: int = 3,
    backoff_base: float = 0.5,
) -> None:
    """Claim & fire *one* timer with extensive logs."""

    logger.debug(
        "[TimerWorker] ▶️ try_claim timer_id=%s status=%s fire_at=%s now=%s",
        timer.timer_id,
        timer.status,
        timer.fire_at,
        now,
    )

    try:
        claimed = await svc.try_fire_and_lock(timer, now=now)
    except Exception as e:
        logger.exception("[TimerWorker] ❗ Exception during try_fire_and_lock: %s", e)
        return

    logger.debug("[TimerWorker] claim_result timer_id=%s claimed=%s", timer.timer_id, claimed)

    if not claimed:
        logger.debug("[TimerWorker] 🚫 Skipped timer_id=%s (not claimed or not due)", timer.timer_id)
        return

    logger.info(
        "[TimerWorker] 🔔 Fired timer_id=%s run_id=%s state=%s fire_at=%s",
        timer.timer_id,
        timer.run_id,
        timer.state_name,
        timer.fire_at,
    )

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug("[TimerWorker] ⏩ Calling advance_workflow run_id=%s attempt=%s", timer.run_id, attempt)
            await advance_workflow(timer.run_id)
            logger.info("[TimerWorker] ✅ advance_workflow success run_id=%s", timer.run_id)
            return
        except Exception as exc:
            logger.warning(
                "[TimerWorker] ⚠️ advance_workflow err run_id=%s attempt=%s/%s → %s",
                timer.run_id,
                attempt,
                max_retries,
                exc,
            )
            if attempt == max_retries:
                logger.exception("[TimerWorker] ❌ give_up run_id=%s", timer.run_id)
                return
            await sleep(backoff_base * (2 ** (attempt - 1)))


# -----------------------------------------------------------------------------
# Poll loop
# -----------------------------------------------------------------------------


async def _poll_once(
    session: AsyncSession,
    *,
    shard_id: int,
    fetch_limit: int,
) -> None:
    logger.debug("[TimerWorker] 🔁 _poll_once start shard_id=%s", shard_id)

    svc = TimerService(TimerRepository(session))
    now = datetime.now(UTC)

    logger.debug("[TimerWorker] ⏳ Now = %s (UTC)", now)

    try:
        timers: Sequence[Timer] = await svc.find_due_timers(
            cutoff=now,
            shard_id=shard_id,
            limit=fetch_limit,
        )
    except Exception as e:
        logger.exception("[TimerWorker] ❗ Exception during find_due_timers: %s", e)
        return

    logger.debug("[TimerWorker] 📦 shard_id=%s found_due=%s", shard_id, len(timers))

    if not timers:
        logger.debug("[TimerWorker] ⛔ No due timers found for shard_id=%s", shard_id)
        return

    await gather(*(process_single_timer(t, svc, now=now) for t in timers))


async def run_timer_loop(
    *,
    session_factory: Callable[[], AsyncGenerator[AsyncSession, None]] = get_db_session,
    interval_seconds: float = 1.0,
    shard_id: int = 0,
    fetch_limit: int = 100,
) -> None:
    logger.info(
        "[TimerWorker] ▶️ loop start interval=%s shard_id=%s fetch_limit=%s",
        interval_seconds,
        shard_id,
        fetch_limit,
    )

    while True:
        logger.debug("[TimerWorker] 🧪 Entered polling loop before session_factory")

        # ✅ 用 async for 解构 generator
        async for session in session_factory():
            try:
                logger.debug("[TimerWorker] 🔂 Starting one polling iteration")
                await _poll_once(session, shard_id=shard_id, fetch_limit=fetch_limit)
            except Exception as err:
                logger.exception("[TimerWorker] 💥 Unhandled error in polling loop: %s", err)
            finally:
                await session.close()  # 避免残留连接
            break  # ⚠️ 只取一次 session，别死循环 async for！

        await sleep(interval_seconds)