"""Webhook trigger business logic."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.events_service import EventsService
from app.core.exceptions.http_exceptions import NotFoundException
from app.core.utils.webhook_url import validate_outbound_webhook_url
from app.crud.crud_triggers import crud_triggers


class TriggerService:
    """Webhook trigger operations scoped to tenant/project."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
    ) -> None:
        """Initialize the service with database session and tenant scope."""
        self.db = db
        self.tenant_id = tenant_id
        self.project_id = project_id

    async def list(self) -> list[dict[str, Any]]:
        """Return all webhook triggers for the tenant/project."""
        return await crud_triggers.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one webhook trigger by ID."""
        record = await crud_triggers.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new webhook trigger."""
        validate_outbound_webhook_url(data["webhook_url"])
        payload = self._prepare_payload(data)
        return await crud_triggers.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            data=payload,
        )

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing webhook trigger."""
        if "webhook_url" in data and data["webhook_url"] is not None:
            validate_outbound_webhook_url(data["webhook_url"])
        payload = self._prepare_payload(data)
        if not payload:
            return await self.get(entity_id)
        record = await crud_triggers.update(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            data=payload,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete a webhook trigger."""
        deleted = await crud_triggers.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        return entity_id

    async def test(self, entity_id: str, *, actor: str | None = None) -> dict[str, Any]:
        """Send a test webhook payload for a trigger."""
        trigger = await self.get(entity_id)
        return await EventsService(self.db).test_trigger(trigger=trigger, actor=actor)

    @staticmethod
    def _prepare_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, Enum):
                payload[key] = value.value
            else:
                payload[key] = value
        return payload
