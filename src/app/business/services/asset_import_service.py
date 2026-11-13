"""Import assets from an uploaded workbook."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NoReturn

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.asset_workbook import (
    ImportRow,
    ParsedSheet,
    WorkbookReadError,
    normalize_label,
    parse_asset_workbook,
)
from app.business.services.vendor_service import VendorService
from app.core.exceptions.http_exceptions import ValidationException
from app.core.utils.logger import logger
from app.crud.crud_asset_categories import crud_asset_categories
from app.crud.crud_assets import crud_assets

MAX_IMPORT_BYTES = 15 * 1024 * 1024

_DUPLICATE_CODE = "Asset code already exists for the project"


@dataclass
class VendorResolution:
    """Vendors resolved for the suppliers on accepted rows."""

    by_name: dict[str, dict[str, Any]] = field(default_factory=dict)
    matched: list[dict[str, str]] = field(default_factory=list)
    created: list[dict[str, str]] = field(default_factory=list)
    unlinked: list[str] = field(default_factory=list)


class AssetImportService:
    """Create assets from one worksheet for the current tenant and project."""

    def __init__(self, db: AsyncSession, tenant_id: str, project_id: str) -> None:
        """Initialize the service with database session and tenant scope."""
        self.db = db
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.vendors = VendorService(db, tenant_id, project_id)

    async def import_workbook(
        self,
        content: bytes,
        *,
        filename: str,
        sheet_name: str | None,
    ) -> dict[str, Any]:
        """Import one worksheet and return created codes, row errors, and vendors."""
        requested = (sheet_name or "").strip() or None
        _validate_upload(filename, content)
        parsed = _parse_or_raise(content, requested)
        await crud_assets.release_deleted_codes(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            codes={row.code for row in parsed.rows},
        )
        categories = await self._category_index()
        existing_codes = await crud_assets.list_codes(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        accepted, errors = _reject_existing_codes(parsed, existing_codes)
        await self._ensure_categories(accepted, categories)
        vendors = await self._resolve_vendors(accepted)
        created_codes = await self._insert_rows(accepted, categories, vendors, errors)
        return _result(parsed, created_codes, errors, vendors)

    async def _category_index(self) -> dict[str, str]:
        records = await crud_asset_categories.list_active(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        categories: dict[str, str] = {}
        for record in records:
            if not record.get("name"):
                continue
            categories.setdefault(normalize_label(record["name"]), record["id"])
        return categories

    async def _ensure_categories(self, rows: list[ImportRow], categories: dict[str, str]) -> None:
        for row in rows:
            key = normalize_label(row.category_name)
            if key in categories:
                continue
            existing = await self._category_by_label(key)
            if existing:
                categories[key] = existing
                continue
            try:
                async with self.db.begin_nested():
                    created = await crud_asset_categories.create(
                        self.db,
                        tenant_id=self.tenant_id,
                        project_id=self.project_id,
                        name=row.category_name,
                    )
            except IntegrityError:
                existing = await self._category_by_label(key)
                if not existing:
                    raise
                categories[key] = existing
                continue
            categories[key] = created["id"]

    async def _category_by_label(self, label: str) -> str | None:
        record = await crud_asset_categories.get_active_by_label(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            label=label,
        )
        if not record:
            return None
        return record["id"]

    async def _resolve_vendors(self, rows: list[ImportRow]) -> VendorResolution:
        resolution = VendorResolution()
        local = await self.vendors.list_local_vendors()
        local_index = _index_vendors(local)
        for key, display in _distinct_suppliers(rows):
            vendor = local_index.get(key) or await self._search_vendor(display)
            if vendor:
                _remember(resolution, key, vendor, resolution.matched)
                continue
            await self._create_vendor(key, display, resolution)
        return resolution

    async def _search_vendor(self, display: str) -> dict[str, Any] | None:
        try:
            result = await self.vendors.search(display)
        except Exception as exc:  # — House of Apps failures stay row-local
            logger.warning("Vendor search failed for %s: %s", display, exc)
            return None
        key = normalize_label(display)
        for vendor in result.get("data", []):
            vendor_name = vendor.get("name")
            if vendor.get("id") and vendor_name and normalize_label(str(vendor_name)) == key:
                return vendor
        return None

    async def _create_vendor(self, key: str, display: str, resolution: VendorResolution) -> None:
        try:
            record = await self.vendors.create(display)
        except Exception as exc:  # — a vendor failure must not drop the asset row
            logger.warning("Vendor create failed for %s: %s", display, exc)
            resolution.unlinked.append(display)
            return
        vendor_id = record.get("id")
        if not vendor_id:
            resolution.unlinked.append(display)
            return
        if not record.get("name"):
            record = {**record, "name": display}
        _remember(resolution, key, record, resolution.created)

    async def _insert_rows(
        self,
        rows: list[ImportRow],
        categories: dict[str, str],
        vendors: VendorResolution,
        errors: list[dict[str, Any]],
    ) -> list[str]:
        ready: list[ImportRow] = []
        payloads: list[dict[str, Any]] = []
        for row in rows:
            category_id = categories.get(normalize_label(row.category_name))
            if not category_id:
                errors.append(_row_error(row, "category", "Category is not a template value"))
                continue
            ready.append(row)
            payloads.append(_asset_payload(row, category_id, vendors))
        if not payloads:
            return []
        try:
            async with self.db.begin_nested():
                return await crud_assets.create_many(
                    self.db,
                    tenant_id=self.tenant_id,
                    project_id=self.project_id,
                    items=payloads,
                )
        except IntegrityError:
            logger.warning("Asset import batch conflicted with an existing code")
            for row in ready:
                errors.append(_row_error(row, "code", _DUPLICATE_CODE))
            return []


def _validate_upload(filename: str, content: bytes) -> None:
    if not filename.lower().endswith(".xlsx"):
        _raise_validation("Import file must be an .xlsx workbook")
    if not content:
        _raise_validation("Import file is empty")
    if len(content) > MAX_IMPORT_BYTES:
        _raise_validation("Import file exceeds the 15 MB limit")


def _parse_or_raise(content: bytes, sheet_name: str | None) -> ParsedSheet:
    try:
        return parse_asset_workbook(content, sheet_name)
    except WorkbookReadError as exc:
        _raise_validation(exc.message)


def _raise_validation(message: str) -> NoReturn:
    raise ValidationException(
        message_key="errors.validation",
        status_code=status.HTTP_400_BAD_REQUEST,
        params={"message": message},
        errors=[{"field": "file", "type": "value_error", "msg": message}],
    )


def _reject_existing_codes(
    parsed: ParsedSheet,
    existing_codes: set[str],
) -> tuple[list[ImportRow], list[dict[str, Any]]]:
    accepted: list[ImportRow] = []
    errors = [error.as_dict() for error in parsed.errors]
    for row in parsed.rows:
        if row.code in existing_codes:
            errors.append(_row_error(row, "code", _DUPLICATE_CODE))
            continue
        accepted.append(row)
    return accepted, errors


def _distinct_suppliers(rows: list[ImportRow]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    names: list[tuple[str, str]] = []
    for row in rows:
        if not row.supplier:
            continue
        display = row.supplier.strip()
        key = normalize_label(display)
        if not key or key in seen:
            continue
        seen.add(key)
        names.append((key, display))
    return names


def _index_vendors(vendors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for vendor in vendors:
        name = vendor.get("name")
        if not vendor.get("id") or not name:
            continue
        indexed.setdefault(normalize_label(str(name)), vendor)
    return indexed


def _remember(
    resolution: VendorResolution,
    key: str,
    vendor: dict[str, Any],
    bucket: list[dict[str, str]],
) -> None:
    resolution.by_name[key] = vendor
    bucket.append({"name": str(vendor.get("name") or ""), "id": str(vendor["id"])})


def _supplier_fields(
    row: ImportRow,
    vendors: VendorResolution,
) -> tuple[str | None, str | None]:
    if not row.supplier:
        return None, None
    vendor = vendors.by_name.get(normalize_label(row.supplier))
    if not vendor:
        return row.supplier.strip(), None
    return str(vendor.get("name") or row.supplier.strip()), str(vendor["id"])


def _asset_payload(row: ImportRow, category_id: str, vendors: VendorResolution) -> dict[str, Any]:
    supplier, supplier_id = _supplier_fields(row, vendors)
    custom: dict[str, Any] = {}
    if row.quantity:
        custom["quantity"] = row.quantity
    return {
        "name": row.name,
        "code": row.code,
        "category_id": category_id,
        "make": row.make,
        "model": row.model,
        "serial_number": row.serial_number,
        "description": row.description,
        "status": row.status,
        "location_text": row.location_text,
        "landmark_note": row.landmark_note,
        "photos": [],
        "associated_parts": [],
        "purchase_date": row.purchase_date,
        "purchase_cost": row.purchase_cost,
        "currency": "INR",
        "supplier": supplier,
        "supplier_vendor_id": supplier_id,
        "invoice_ref": row.invoice_ref,
        "install_date": row.install_date,
        "warranty_expiry": row.warranty_expiry,
        "warranty_terms": row.warranty_terms,
        "documents": [],
        "custom_field_values": custom,
    }


def _row_error(row: ImportRow, field: str, message: str) -> dict[str, Any]:
    return {"row": row.excel_row, "field": field, "message": message}


def _result(
    parsed: ParsedSheet,
    created_codes: list[str],
    errors: list[dict[str, Any]],
    vendors: VendorResolution,
) -> dict[str, Any]:
    errors.sort(key=lambda item: (item["row"], item["field"]))
    return {
        "sheet": parsed.sheet,
        "total_rows": parsed.total_rows,
        "created": len(created_codes),
        "failed": len(errors),
        "errors": errors,
        "created_codes": created_codes,
        "vendors_matched": vendors.matched,
        "vendors_created": vendors.created,
        "vendors_unlinked": vendors.unlinked,
    }
