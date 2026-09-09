"""
SATVIGIL — APScheduler: Periodic Data Fetch Jobs

Schedule:
  AIS vessels     → every 15 minutes
  FIRMS thermal   → every 3 hours
  Sentinel-2      → every 24 hours (image availability check)
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
import structlog

logger = structlog.get_logger()
scheduler = AsyncIOScheduler()


async def job_fetch_ais():
    """Fetch AIS vessel data and update risk scores."""
    logger.info("scheduler_job_start", job="fetch_ais")
    from app.tasks.ais_worker import run_ais_ingest
    await run_ais_ingest()
    logger.info("scheduler_job_done", job="fetch_ais")


async def job_fetch_firms():
    """Fetch NASA FIRMS thermal data, classify, and store alerts."""
    logger.info("scheduler_job_start", job="fetch_firms")
    from app.services.fire.firms_fetcher import fetch_firms_india
    df = await fetch_firms_india(days=1)
    # TODO: Classify each hotspot, check recurrence, store to DB
    logger.info("scheduler_job_done", job="fetch_firms", hotspots=len(df))


async def job_check_sentinel():
    """Check Copernicus for new Sentinel-2 images over India."""
    logger.info("scheduler_job_start", job="check_sentinel")
    # TODO: Query Copernicus Dataspace API for new scenes
    logger.info("scheduler_job_done", job="check_sentinel")


def start_scheduler():
    scheduler.add_job(
        job_fetch_ais,
        trigger=IntervalTrigger(seconds=settings.AIS_FETCH_INTERVAL_SECONDS),
        id="fetch_ais",
        replace_existing=True,
    )
    scheduler.add_job(
        job_fetch_firms,
        trigger=IntervalTrigger(seconds=settings.FIRMS_FETCH_INTERVAL_SECONDS),
        id="fetch_firms",
        replace_existing=True,
    )
    scheduler.add_job(
        job_check_sentinel,
        trigger=IntervalTrigger(seconds=settings.SENTINEL_FETCH_INTERVAL_SECONDS),
        id="check_sentinel",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler_started", jobs=["fetch_ais", "fetch_firms", "check_sentinel"])


def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("scheduler_stopped")
