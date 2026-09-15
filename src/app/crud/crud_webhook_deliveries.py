"""Database operations for webhook delivery logs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger_config import TriggerConfig
from app.models.webhook_delivery import WebhookDelivery


class CRUDWebhookDelivery:
    """CRUD operations for webhook delivery logs."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List webhook delivery logs and return rows with the total count."""
        filters = [
            WebhookDelivery.tenant_id == tenant_id,
            WebhookDelivery.project_id == project_id,
        ]

        count_stmt = select(func.count()).select_from(WebhookDelivery).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(WebhookDelivery)
            .where(*filters)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_webhook_delivery_to_dict(row) for row in rows], total

    async def list_pending(
        self,
        db: AsyncSession,
        *,
        limit: int = 100,
        after_id: str | None = None,
        max_attempts: int = 3,
    ) -> list[dict[str, Any]]:
        """List pending webhook deliveries eligible for retry."""
        filters = [
            WebhookDelivery.delivered.is_(False),
            WebhookDelivery.attempt < max_attempts,
        ]
        if after_id:
            filters.append(WebhookDelivery.id > after_id)

        stmt = (
            select(
                WebhookDelivery,
                TriggerConfig.webhook_url,
                TriggerConfig.secret,
            )
            .outerjoin(TriggerConfig, TriggerConfig.id == WebhookDelivery.trigger_id)
            .where(*filters)
            .order_by(WebhookDelivery.id.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()
        pending: list[dict[str, Any]] = []
        for delivery, webhook_url, secret in rows:
            item = _webhook_delivery_to_dict(delivery)
            item["webhook_url"] = webhook_url
            item["secret"] = secret
            pending.append(item)
        return pending

    async def claim_pending_batch(
        self,
        db: AsyncSession,
        *,
        limit: int = 50,
        max_attempts: int = 3,
    ) -> list[dict[str, Any]]:
        """Claim pending deliveries using ``FOR UPDATE SKIP LOCKED``."""
        stmt = (
            select(
                WebhookDelivery,
                TriggerConfig.webhook_url,
                TriggerConfig.secret,
            )
            .outerjoin(TriggerConfig, TriggerConfig.id == WebhookDelivery.trigger_id)
            .where(
                WebhookDelivery.delivered.is_(False),
                WebhookDelivery.attempt < max_attempts,
            )
            .order_by(WebhookDelivery.id.asc())
            .limit(limit)
            .with_for_update(of=WebhookDelivery, skip_locked=True)
        )
        result = await db.execute(stmt)
        rows = result.all()
        pending: list[dict[str, Any]] = []
        for delivery, webhook_url, secret in rows:
            item = _webhook_delivery_to_dict(delivery)
            item["webhook_url"] = webhook_url
            item["secret"] = secret
            pending.append(item)
        return pending

    async def update_result(
        self,
        db: AsyncSession,
        delivery_id: str,
        *,
        response_status: int | None,
        error: str | None,
        attempt: int,
        duration_ms: int,
        delivered: bool,
    ) -> None:
        """Update delivery attempt results for a webhook delivery."""
        stmt = (
            update(WebhookDelivery)
            .where(WebhookDelivery.id == delivery_id)
            .values(
                response_status=response_status,
                error=error,
                attempt=attempt,
                duration_ms=duration_ms,
                delivered=delivered,
            )
        )
        await db.execute(stmt)

    async def create(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new webhook delivery record."""
        row = WebhookDelivery(id=self.new_id(), **data)
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _webhook_delivery_to_dict(row)

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new webhook delivery rows."""
        return f"webhook_delivery_{uuid.uuid4().hex[:12]}"


def _webhook_delivery_to_dict(row: WebhookDelivery) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "trigger_id": row.trigger_id,
        "entity": row.entity,
        "entity_id": row.entity_id,
        "event": row.event,
        "request_payload": dict(row.request_payload or {}),
        "response_status": row.response_status,
        "error": row.error,
        "attempt": row.attempt,
        "duration_ms": row.duration_ms,
        "delivered": row.delivered,
        "created_at": row.created_at,
    }


crud_webhook_deliveries = CRUDWebhookDelivery()
