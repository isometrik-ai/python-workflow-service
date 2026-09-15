"""CLI entry point for the webhook delivery worker."""

from __future__ import annotations

import asyncio
import sys

from app.core.config.app_config import settings
from app.core.setup import cleanup_database, setup_database
from app.core.utils.logger import logger
from app.workers.schedulers.webhook_delivery_worker import webhook_delivery_worker


async def main() -> None:
    """Run the webhook delivery worker until interrupted."""
    try:
        await setup_database(settings)
        await webhook_delivery_worker.run_forever()
    except KeyboardInterrupt:
        logger.info("Webhook delivery worker interrupted by user")
    except Exception as exc:
        logger.exception("Fatal error in webhook delivery worker: %s", exc)
        sys.exit(1)
    finally:
        await webhook_delivery_worker.stop()
        await cleanup_database()
        logger.info("Webhook delivery worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Webhook delivery worker shutdown complete")
    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        sys.exit(1)
