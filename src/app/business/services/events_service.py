"""Audit events and webhook dispatch pipeline."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.webhook_url import validate_outbound_webhook_url
from app.crud.crud_audit_events import crud_audit_events
from app.crud.crud_triggers import crud_triggers
from app.crud.crud_webhook_deliveries import crud_webhook_deliveries
from app.schemas.common import AuditSource

VALID_SOURCES = frozenset(source.value for source in AuditSource)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _deep_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_deep_safe(item) for item in value]
    return _json_safe(value)


def snapshot_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-serializable copy of a record."""
    return _deep_safe(record)


def diff_records(
    before: dict[str, Any],
    after: dict[str, Any],
    skip: tuple[str, ...] = ("updated_at",),
) -> list[dict[str, Any]]:
    """Return field-level changes between two record snapshots."""
    changes: list[dict[str, Any]] = []
    for field, new in after.items():
        if field in skip:
            continue
        old = before.get(field)
        if old != new:
            changes.append({"field": field, "old": _deep_safe(old), "new": _deep_safe(new)})
    return changes


def entity_label(record: dict[str, Any]) -> str | None:
    """Return a human-readable label from a record."""
    for attr in ("title", "name", "invoice_number", "label"):
        value = record.get(attr)
        if value:
            return str(value)[:256]
    return None


def event_for(action: str, changes: list[dict[str, Any]]) -> str:
    """Map an action and changes to the webhook event name."""
    if action == "updated" and any(change["field"] in ("state", "status") for change in changes):
        return "status_changed"
    return action


class EventsService:
    """Record audit rows and enqueue webhook deliveries."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    async def record_and_dispatch(
        self,
        *,
        entity: str,
        action: str,
        record: dict[str, Any],
        changes: list[dict[str, Any]] | None = None,
        actor: str | None = None,
        source: str = AuditSource.FM.value,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        """Persist an audit event and enqueue matching webhook deliveries."""
        org_id = tenant_id or record.get("tenant_id")
        proj_id = project_id or record.get("project_id")
        if not org_id or not proj_id:
            return

        changes = changes or []
        event = event_for(action, changes)
        snapshot = snapshot_record(record)
        safe_source = source if source in VALID_SOURCES else AuditSource.FM.value

        await crud_audit_events.create(
            self.db,
            data={
                "tenant_id": org_id,
                "project_id": proj_id,
                "entity": entity,
                "entity_id": record["id"],
                "entity_label": entity_label(record),
                "action": action,
                "actor": actor,
                "source": safe_source,
                "changes": changes,
                "snapshot": snapshot,
            },
        )

        triggers = await crud_triggers.list_matching_triggers(
            self.db,
            tenant_id=org_id,
            project_id=proj_id,
            entity=entity,
            event=event,
        )
        if not triggers:
            return

        payload = {
            "id": str(uuid.uuid4()),
            "at": _now_iso(),
            "entity": entity,
            "entity_id": record.get("id"),
            "entity_label": entity_label(record),
            "action": action,
            "actor": actor,
            "source": safe_source,
            "changes": _deep_safe(changes),
            "snapshot": snapshot,
        }
        for trigger in triggers:
            await crud_webhook_deliveries.create(
                self.db,
                data={
                    "tenant_id": org_id,
                    "project_id": proj_id,
                    "trigger_id": trigger["id"],
                    "entity": entity,
                    "entity_id": record.get("id"),
                    "event": f"{entity}.{event}",
                    "request_payload": payload,
                    "delivered": False,
                },
            )

    async def test_trigger(
        self,
        *,
        trigger: dict[str, Any],
        actor: str | None = None,
    ) -> dict[str, Any]:
        """Fire a sample payload at a trigger and record the delivery."""
        from app.core.services.webhook_client import post_webhook

        started = datetime.now(timezone.utc)
        validate_outbound_webhook_url(trigger["webhook_url"])
        payload = {
            "id": str(uuid.uuid4()),
            "at": _now_iso(),
            "entity": trigger["entity"],
            "entity_id": "test",
            "entity_label": "Test event",
            "action": "test",
            "actor": actor,
            "source": AuditSource.FM.value,
            "changes": [],
            "snapshot": {"note": "Test event from triggers page."},
        }
        event = f"{trigger['entity']}.test"
        status_code, error = await post_webhook(
            trigger["webhook_url"],
            secret=trigger.get("secret"),
            event=event,
            payload=payload,
        )
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        delivered = status_code is not None and 200 <= status_code < 300
        await crud_webhook_deliveries.create(
            self.db,
            data={
                "tenant_id": trigger["tenant_id"],
                "project_id": trigger["project_id"],
                "trigger_id": trigger["id"],
                "entity": trigger["entity"],
                "entity_id": "test",
                "event": event,
                "request_payload": payload,
                "response_status": status_code,
                "error": error or (None if delivered else f"endpoint returned {status_code}"),
                "attempt": 1,
                "duration_ms": duration_ms,
                "delivered": delivered,
            },
        )
        return {
            "delivered": delivered,
            "status": status_code,
            "error": error,
            "duration_ms": duration_ms,
        }
