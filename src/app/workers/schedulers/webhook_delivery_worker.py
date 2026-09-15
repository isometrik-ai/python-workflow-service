"""DB-driven webhook delivery worker with retries."""

from __future__ import annotations

import asyncio
import signal
from datetime import UTC, datetime
from typing import Any

from app.core.config.app_config import settings
from app.core.db.postgres.database import async_get_db_session
from app.core.services.webhook_client import post_webhook
from app.core.utils.logger import logger
from app.core.utils.webhook_url import validate_outbound_webhook_url
from app.crud.crud_webhook_deliveries import crud_webhook_deliveries

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (5, 30)


async def _post_with_retries(item: dict[str, Any]) -> tuple[int | None, str | None, int]:
    """Attempt delivery with inline retries; returns status, error, attempts used."""
    prior_attempts = int(item.get("attempt") or 0)
    status: int | None = None
    error: str | None = None
    attempts = prior_attempts

    for attempt in range(prior_attempts + 1, MAX_ATTEMPTS + 1):
        attempts = attempt
        try:
            validate_outbound_webhook_url(item["webhook_url"])
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}", attempts

        status, error = await post_webhook(
            item["webhook_url"],
            secret=item.get("secret"),
            event=item["event"],
            payload=item.get("request_payload") or {},
        )
        if status is not None and 200 <= status < 300:
            return status, None, attempts
        if attempt < MAX_ATTEMPTS:
            await asyncio.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])

    return status, error, attempts


async def deliver_webhook(item: dict[str, Any]) -> None:
    """POST one webhook delivery row and persist the attempt result."""
    prior_attempts = int(item.get("attempt") or 0)
    if prior_attempts >= MAX_ATTEMPTS:
        logger.warning(
            "Skipping webhook delivery %s — attempt limit reached",
            item.get("id"),
        )
        return

    started = datetime.now(UTC)
    status, error, attempts = await _post_with_retries(item)
    duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    delivered = status is not None and 200 <= status < 300
    if not delivered and error is None:
        error = f"endpoint returned {status}"

    delivery_id = item.get("id")
    if not delivery_id:
        logger.warning("Webhook delivery item missing id — cannot persist result")
        return

    try:
        async with async_get_db_session() as db:
            await crud_webhook_deliveries.update_result(
                db,
                delivery_id,
                response_status=status,
                error=error,
                attempt=attempts,
                duration_ms=duration_ms,
                delivered=delivered,
            )
    except Exception:
        logger.exception(
            "Failed to record webhook delivery for trigger %s",
            item.get("trigger_id"),
        )


class WebhookDeliveryWorker:
    """Poll ``webhook_deliveries`` and dispatch pending rows."""

    def __init__(self) -> None:
        """Initialize worker loop state."""
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        self._shutdown_initiated = False

    def _setup_signal_handlers(self) -> None:
        """Register SIGINT/SIGTERM handlers when running as a standalone process."""

        def handler(signum: int, _frame: Any) -> None:
            logger.info("Webhook worker received signal %s, shutting down", signum)
            self.shutdown_event.set()

        try:
            signal.signal(signal.SIGINT, handler)
            signal.signal(signal.SIGTERM, handler)
        except ValueError:
            logger.debug("signal.signal not available in this context")

    async def _claim_batch(self) -> list[dict[str, Any]]:
        """Claim a batch of pending deliveries under row locks."""
        async with async_get_db_session() as db:
            return await crud_webhook_deliveries.claim_pending_batch(
                db,
                limit=settings.WOM_WEBHOOK_WORKER_BATCH_SIZE,
                max_attempts=MAX_ATTEMPTS,
            )

    async def _process_batch(self) -> int:
        """Claim and deliver one batch; returns rows processed."""
        try:
            pending = await self._claim_batch()
        except Exception:
            logger.exception("Webhook worker claim failed")
            return 0

        if not pending:
            return 0

        processed = 0
        for item in pending:
            if self.shutdown_event.is_set():
                break
            if not item.get("webhook_url"):
                logger.warning(
                    "Skipping webhook delivery %s — trigger URL unavailable",
                    item.get("id"),
                )
                continue
            await deliver_webhook(item)
            processed += 1
        return processed

    async def run_forever(self) -> None:
        """Poll the outbox until shutdown."""
        self._setup_signal_handlers()
        self.is_running = True
        interval = max(1, settings.WOM_WEBHOOK_WORKER_INTERVAL_SECONDS)
        logger.info(
            "Webhook delivery worker started (interval=%ss, batch=%s)",
            interval,
            settings.WOM_WEBHOOK_WORKER_BATCH_SIZE,
        )

        try:
            while self.is_running and not self.shutdown_event.is_set():
                try:
                    processed = await self._process_batch()
                    if processed:
                        logger.info("Webhook worker processed %s delivery row(s)", processed)
                except Exception:
                    logger.exception("Webhook worker loop iteration failed")
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=interval)
                    break
                except TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Signal the worker loop to exit."""
        if self._shutdown_initiated:
            return
        self._shutdown_initiated = True
        self.is_running = False
        self.shutdown_event.set()
        logger.info("Webhook delivery worker stopped")


webhook_delivery_worker = WebhookDeliveryWorker()
