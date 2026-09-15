"""CLI entry point for the contract/recurring work-order scheduler."""

from __future__ import annotations

import asyncio
import sys

from app.core.config.app_config import settings
from app.core.setup import cleanup_database, setup_database
from app.core.utils.logger import logger
from app.workers.schedulers.scheduler_worker import run_scheduler_loop


async def main() -> None:
    """Run the scheduler loop until interrupted."""
    if not settings.WOM_SCHEDULER_ENABLED:
        logger.error("WOM_SCHEDULER_ENABLED=false; scheduler worker exiting")
        sys.exit(1)

    try:
        await setup_database(settings)
        await run_scheduler_loop()
    except KeyboardInterrupt:
        logger.info("Scheduler worker interrupted by user")
    except Exception as exc:
        logger.exception("Fatal error in scheduler worker: %s", exc)
        sys.exit(1)
    finally:
        await cleanup_database()
        logger.info("Scheduler worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler worker shutdown complete")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)
