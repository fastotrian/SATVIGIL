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
    """Fetch NASA FIRMS thermal data, classify, and store alerts to PostGIS."""
    logger.info("scheduler_job_start", job="fetch_firms")
    try:
        from app.services.fire.firms_fetcher import fetch_firms_india
        from app.services.fire.firms_processor import ingest_firms_batch
        from app.core.database import AsyncSessionLocal
        
        df = await fetch_firms_india(days=1)
        if df is not None and not df.empty:
            async with AsyncSessionLocal() as db:
                count = await ingest_firms_batch(df, db)
                logger.info("scheduler_job_done", job="fetch_firms", hotspots=len(df), ingested=count)
        else:
            logger.info("scheduler_job_done", job="fetch_firms", hotspots=0)
    except Exception as exc:
        logger.warning("scheduler_firms_job_failed", error=str(exc))


async def job_check_sentinel():
    """Check Copernicus CDSE for new Sentinel-1 C-SAR radar passes over India."""
    logger.info("scheduler_job_start", job="check_sentinel")
    try:
        from app.services.satellite.copernicus_cdse import search_sentinel1_scenes
        scenes = await search_sentinel1_scenes(sector="bombay_high", days_back=7)
        logger.info("scheduler_job_done", job="check_sentinel", scenes_found=len(scenes))
    except Exception as exc:
        logger.warning("scheduler_sentinel_job_failed", error=str(exc))


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
