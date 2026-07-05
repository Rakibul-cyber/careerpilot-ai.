# Scheduler factory + lifecycle.
#
# BackgroundScheduler runs in-process alongside the API (single worker). All
# jobs are max_instances=1 + coalesce=True so a slow run never overlaps itself
# and a burst of missed runs collapses into one. Disabled by default; enabled
# via settings.SCHEDULER_ENABLED.

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.logging import get_logger
from app.scheduler.jobs import (
    archive_jobs_job,
    expire_jobs_job,
    run_due_alerts_job,
    run_mock_connector_job,
)

logger = get_logger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Build a scheduler with all system jobs registered (not started)."""
    scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)

    scheduler.add_job(
        run_mock_connector_job,
        trigger="interval",
        hours=6,
        id="mock_connector_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        expire_jobs_job,
        trigger="interval",
        hours=1,
        id="expire_jobs_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        archive_jobs_job,
        trigger="cron",
        hour=3,
        minute=0,
        id="archive_jobs_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_due_alerts_job,
        trigger="interval",
        minutes=15,
        id="run_due_alerts_job",
        max_instances=1,
        coalesce=True,
    )

    return scheduler


def start_scheduler() -> BackgroundScheduler | None:
    """Start the scheduler if enabled, otherwise log and return None."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false)")
        return None

    scheduler = create_scheduler()
    scheduler.start()
    logger.info(
        "Scheduler started timezone=%s jobs=%s",
        settings.SCHEDULER_TIMEZONE,
        [job.id for job in scheduler.get_jobs()],
    )
    return scheduler


def shutdown_scheduler(scheduler: BackgroundScheduler | None) -> None:
    """Gracefully stop the scheduler if it is running."""
    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
