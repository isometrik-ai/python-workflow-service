"""MCP JSON-RPC tool handlers delegating to existing domain services."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.business_profile_service import BusinessProfileService
from app.business.services.contract_service import ContractService
from app.business.services.invoice_service import InvoiceService
from app.business.services.payment_service import PaymentService
from app.business.services.work_order_service import WorkOrderService
from app.core.exceptions.http_exceptions import ValidationException
from app.schemas.common import ApiKeyScope
from app.schemas.invoices import InvoiceStatus
from app.schemas.work_orders import WorkOrderSource, WorkOrderState

_STATE_ALIASES = {
    "upcoming": WorkOrderState.UPCOMING.value,
    "in progress": WorkOrderState.IN_PROGRESS.value,
    "in_progress": WorkOrderState.IN_PROGRESS.value,
    "in review": WorkOrderState.IN_REVIEW.value,
    "in_review": WorkOrderState.IN_REVIEW.value,
    "completed": WorkOrderState.COMPLETED.value,
    "closed": WorkOrderState.COMPLETED.value,
    "terminated": WorkOrderState.TERMINATED.value,
    "cancelled": WorkOrderState.TERMINATED.value,
}


def mcp_tools() -> list[dict[str, Any]]:
    """Return MCP tool definitions for tools/list."""
    return [
        {
            "name": "list_work_orders",
            "description": "List work orders, newest first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "state": {"type": "string"},
                    "vendor_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        },
        {
            "name": "get_work_order",
            "description": "Get one work order by id.",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        },
        {
            "name": "create_work_order",
            "description": "Create an ad-hoc work order.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "scheduled_date": {"type": "string"},
                    "vendor_id": {"type": "string"},
                    "asset_ids": {"type": "array", "items": {"type": "string"}},
                    "priority": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["title", "scheduled_date", "vendor_id"],
            },
        },
        {
            "name": "update_work_order_status",
            "description": "Move a work order to a new state.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "state": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["id", "state"],
            },
        },
        {
            "name": "list_invoices",
            "description": "List vendor invoices, newest first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        },
        {
            "name": "approve_invoice",
            "description": "Approve a vendor invoice.",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        },
        {
            "name": "reject_invoice",
            "description": "Reject a vendor invoice.",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["id"],
            },
        },
        {
            "name": "request_invoice_revision",
            "description": "Ask the vendor to re-issue an invoice.",
            "inputSchema": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "note": {"type": "string"}},
                "required": ["id"],
            },
        },
        {
            "name": "list_contracts",
            "description": "List maintenance contracts.",
            "inputSchema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 50}},
            },
        },
        {
            "name": "list_payments",
            "description": "List payments, newest first.",
            "inputSchema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 50}},
            },
        },
        {
            "name": "get_business_profile",
            "description": "The issuing business profile used on documents.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]


class McpService:
    """Execute MCP tools against tenant/project-scoped domain services."""

    def __init__(self, db: AsyncSession, scope: ApiKeyScope) -> None:
        """Initialize MCP service with database session and API key scope."""
        self.db = db
        self.scope = scope
        self._actor = f"API key {scope.api_key_name or scope.api_key_id or 'unknown'}"
        self._tool_handlers: dict[str, Any] = {
            "list_work_orders": self._list_work_orders,
            "get_work_order": lambda args: self._get_work_order(args["id"]),
            "create_work_order": self._create_work_order,
            "update_work_order_status": self._update_work_order_status,
            "list_invoices": self._list_invoices,
            "approve_invoice": lambda args: self._approve_invoice(args["id"]),
            "reject_invoice": lambda args: self._reject_invoice(args["id"], args.get("reason")),
            "request_invoice_revision": lambda args: self._request_invoice_revision(
                args["id"],
                args.get("note"),
            ),
            "list_contracts": self._list_contracts,
            "list_payments": self._list_payments,
            "get_business_profile": lambda _args: self._get_business_profile(),
        }

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Dispatch an MCP tool call to the appropriate domain service."""
        handler = self._tool_handlers.get(name)
        if handler is None:
            raise ValidationException(message_key="errors.validation_failed")
        return await handler(args)

    async def _list_work_orders(self, args: dict[str, Any]) -> dict[str, Any]:
        service = WorkOrderService(self.db, self.scope.tenant_id, self.scope.project_id)
        limit = int(args.get("limit") or 50)
        state = _normalize_state(args.get("state")) if args.get("state") else None
        items, _ = await service.list(page=1, page_size=limit, state=state)
        vendor_id = args.get("vendor_id")
        if vendor_id:
            items = [row for row in items if row.get("vendor_id") == vendor_id]
        return {"data": items[:limit]}

    async def _get_work_order(self, entity_id: str) -> dict[str, Any]:
        service = WorkOrderService(self.db, self.scope.tenant_id, self.scope.project_id)
        return await service.get(entity_id)

    async def _create_work_order(self, args: dict[str, Any]) -> dict[str, Any]:
        service = WorkOrderService(self.db, self.scope.tenant_id, self.scope.project_id)
        scheduled = args.get("scheduled_date")
        scheduled_date = date.fromisoformat(str(scheduled)) if scheduled else None
        payload = {
            "title": args["title"],
            "scheduled_date": scheduled_date,
            "vendor_id": args["vendor_id"],
            "asset_ids": args.get("asset_ids") or [],
            "priority": args.get("priority") or "medium",
            "description": args.get("description"),
            "source": WorkOrderSource.AD_HOC.value,
        }
        return await service.create(payload)

    async def _update_work_order_status(self, args: dict[str, Any]) -> dict[str, Any]:
        service = WorkOrderService(self.db, self.scope.tenant_id, self.scope.project_id)
        entity_id = args["id"]
        state = _normalize_state(args["state"])
        if not state:
            raise ValidationException(message_key="errors.validation_failed")
        record = await service.update(entity_id, {"state": state})
        note = args.get("note")
        if note:
            await service.append_timeline(
                entity_id,
                event_type="status_changed",
                note=note,
                by=self._actor,
            )
            record = await service.get(entity_id)
        return {"id": record["id"], "state": record.get("state")}

    async def _list_invoices(self, args: dict[str, Any]) -> dict[str, Any]:
        service = InvoiceService(self.db, self.scope.tenant_id, self.scope.project_id)
        limit = int(args.get("limit") or 50)
        items, total = await service.list(
            page=1,
            page_size=limit,
            status=args.get("status"),
        )
        return {"total": total, "data": items}

    async def _approve_invoice(self, entity_id: str) -> dict[str, Any]:
        service = InvoiceService(self.db, self.scope.tenant_id, self.scope.project_id)
        return await service.update(entity_id, {"status": InvoiceStatus.APPROVED.value})

    async def _reject_invoice(self, entity_id: str, reason: str | None) -> dict[str, Any]:
        service = InvoiceService(self.db, self.scope.tenant_id, self.scope.project_id)
        return await service.update(
            entity_id,
            {"status": InvoiceStatus.REJECTED.value, "note": reason},
        )

    async def _request_invoice_revision(self, entity_id: str, note: str | None) -> dict[str, Any]:
        service = InvoiceService(self.db, self.scope.tenant_id, self.scope.project_id)
        message = f"Revision requested: {note or ''}".strip()
        return await service.update(
            entity_id,
            {"status": InvoiceStatus.REVISION_REQUESTED.value, "note": message},
        )

    async def _list_contracts(self, args: dict[str, Any]) -> dict[str, Any]:
        service = ContractService(self.db, self.scope.tenant_id, self.scope.project_id)
        limit = int(args.get("limit") or 50)
        items, total = await service.list(page=1, page_size=limit)
        return {"total": total, "data": items}

    async def _list_payments(self, args: dict[str, Any]) -> dict[str, Any]:
        service = PaymentService(self.db, self.scope.tenant_id, self.scope.project_id)
        limit = int(args.get("limit") or 50)
        items, total = await service.list(page=1, page_size=limit)
        return {"total": total, "data": items}

    async def _get_business_profile(self) -> dict[str, Any]:
        service = BusinessProfileService(self.db, self.scope.tenant_id, self.scope.project_id)
        return await service.get()


def _normalize_state(raw: str | None) -> str | None:
    """Map reference-style state strings to internal enum values."""
    if raw is None:
        return None
    return _STATE_ALIASES.get(raw.strip().lower(), raw.strip().lower())


def json_safe(value: Any) -> Any:
    """Serialize values for MCP JSON-RPC text content."""
    return json.loads(json.dumps(value, default=str))
