"""Background scheduler loop with Postgres advisory lock."""

from __future__ import annotations

import asyncio

from app.business.services.scheduler_service import SchedulerService
from app.core.config.app_config import settings
from app.core.db.postgres.database import async_get_db_session
from app.core.utils.logger import logger


async def run_scheduler_once() -> dict[str, int]:
    """Run one scheduler sweep under advisory lock."""
    async with async_get_db_session() as db:
        service = SchedulerService(db)
        return await service.run_once()


async def run_scheduler_loop() -> None:
    """Periodic scheduler loop."""
    interval = max(1, settings.WOM_SCHEDULER_INTERVAL_MINUTES) * 60
    logger.info("Scheduler loop interval=%ss", interval)
    while True:
        try:
            result = await run_scheduler_once()
            if result.get("created") or result.get("cancelled"):
                logger.info("Scheduler run: %s", result)
        except Exception:
            logger.exception("Scheduler run failed")
        await asyncio.sleep(interval)
