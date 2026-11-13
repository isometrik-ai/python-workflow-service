"""Parse asset import workbooks into row payloads."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from typing import Any
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.schemas.assets import AssetStatus

HEADER_FIELDS = {
    "asset name": "name",
    "asset code / tag no": "code",
    "category": "category",
    "make": "make",
    "make / brand": "make",
    "model": "model",
    "serial number": "serial_number",
    "status": "status",
    "location": "location",
    "landmark": "landmark",
    "purchase date": "purchase_date",
    "purchase cost": "purchase_cost",
    "supplier / vendor": "supplier",
    "invoice / po no": "invoice_ref",
    "installation date": "install_date",
    "warranty end": "warranty_expiry",
    "warranty / amc details": "warranty_terms",
    "notes": "description",
    "quantity": "quantity",
}

TEMPLATE_CATEGORIES = {
    "hvac": "HVAC",
    "electrical": "Electrical",
    "dg set": "DG Set",
    "lift": "Lift",
    "plumbing": "Plumbing",
    "fire safety": "Fire Safety",
    "security / cctv": "Security / CCTV",
    "it / network": "IT / Network",
    "pumps & motors": "Pumps & Motors",
    "stp / wtp": "STP / WTP",
    "furniture": "Furniture",
    "gym equipment": "Gym Equipment",
    "other": "Other",
}

STATUS_MAP = {
    "working": AssetStatus.OPERATIONAL.value,
    "under maintenance": AssetStatus.UNDER_REPAIR.value,
    "not working": AssetStatus.FAULTY.value,
    "retired": AssetStatus.DECOMMISSIONED.value,
}

_HINT_NAMES = {"what you call it"}
_HINT_CATEGORIES = {"pick from list"}
_NUMERIC_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_PLAIN_NUMBER = re.compile(r"\d+(\.0+)?")
_BIGINT_MAX = 9_223_372_036_854_775_807
_HEADER_SCAN_ROWS = 20
_OPTIONAL_TEXT = (
    ("make", 255, "make", "Make"),
    ("model", 255, "model", "Model"),
    ("serial_number", 255, "serial_number", "Serial number"),
    ("location", 500, "location", "Location"),
    ("landmark", 500, "landmark", "Landmark"),
    ("supplier", 255, "supplier", "Supplier / Vendor"),
    ("invoice_ref", 100, "invoice_ref", "Invoice / PO No."),
    ("warranty_terms", 2000, "warranty_terms", "Warranty / AMC details"),
    ("description", 4000, "notes", "Notes"),
    ("quantity", 255, "quantity", "Quantity"),
)
_DATE_FIELDS = (
    ("purchase_date", "purchase_date", "Purchase date"),
    ("install_date", "install_date", "Installation date"),
    ("warranty_expiry", "warranty_expiry", "Warranty end"),
)


class WorkbookReadError(Exception):
    """The workbook cannot be imported."""

    def __init__(self, message: str) -> None:
        """Store a caller-facing reason."""
        super().__init__(message)
        self.message = message


class _CellError(Exception):
    """One cell failed to parse."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass
class ImportRowError:
    """A worksheet row that cannot become an asset."""

    row: int
    field: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        """Return the API error shape."""
        return {"row": self.row, "field": self.field, "message": self.message}


@dataclass
class ImportRow:  # pylint: disable=too-many-instance-attributes
    """One valid asset row, still missing category and vendor ids."""

    excel_row: int
    name: str
    code: str
    category_name: str
    status: str
    make: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location_text: str | None = None
    landmark_note: str | None = None
    purchase_date: date | None = None
    purchase_cost: int | None = None
    supplier: str | None = None
    invoice_ref: str | None = None
    install_date: date | None = None
    warranty_expiry: date | None = None
    warranty_terms: str | None = None
    description: str | None = None
    quantity: str | None = None


@dataclass
class ParsedSheet:
    """Rows read from a single worksheet."""

    sheet: str
    total_rows: int
    rows: list[ImportRow]
    errors: list[ImportRowError]


def normalize_label(value: str) -> str:
    """Return a case-folded label with collapsed whitespace."""
    return " ".join(value.replace("\xa0", " ").split()).lower()


def parse_asset_workbook(content: bytes, sheet_name: str | None) -> ParsedSheet:
    """Read one worksheet into asset rows and row errors."""
    worksheet = _open_worksheet(content, sheet_name)
    _expand_merged_cells(worksheet)
    header_row, columns = _find_header(worksheet)
    return _collect_rows(worksheet, header_row, columns)


def _open_worksheet(content: bytes, sheet_name: str | None) -> Worksheet:
    workbook = _load_workbook(content)
    requested = sheet_name or "Assets"
    match = _match_sheet(workbook, requested)
    if match is None:
        raise WorkbookReadError(f"Sheet '{requested}' was not found")
    return workbook[match]


def _load_workbook(content: bytes) -> Workbook:
    try:
        return load_workbook(BytesIO(content), data_only=True)
    except (BadZipFile, InvalidFileException, OSError, ValueError, EOFError) as exc:
        raise WorkbookReadError("File is not a valid .xlsx workbook") from exc


def _match_sheet(workbook: Workbook, sheet_name: str) -> str | None:
    target = sheet_name.strip().lower()
    for name in workbook.sheetnames:
        if name.strip().lower() == target:
            return name
    return None


def _expand_merged_cells(worksheet: Worksheet) -> None:
    ranges = list(worksheet.merged_cells.ranges)
    for merged in ranges:
        min_row, min_col = merged.min_row, merged.min_col
        max_row, max_col = merged.max_row, merged.max_col
        value = worksheet.cell(min_row, min_col).value
        worksheet.unmerge_cells(
            start_row=min_row,
            start_column=min_col,
            end_row=max_row,
            end_column=max_col,
        )
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                worksheet.cell(row, col).value = value


def _find_header(worksheet: Worksheet) -> tuple[int, dict[str, int]]:
    last = min(worksheet.max_row or 1, _HEADER_SCAN_ROWS)
    for excel_row in range(1, last + 1):
        mapping = _header_map(worksheet, excel_row)
        if mapping is None:
            continue
        _ensure_required_columns(mapping)
        return excel_row, mapping
    raise WorkbookReadError("Selected sheet has no asset header row")


def _header_map(worksheet: Worksheet, excel_row: int) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    last_column = worksheet.max_column or 1
    for col in range(1, last_column + 1):
        raw = worksheet.cell(excel_row, col).value
        if raw is None:
            continue
        field = HEADER_FIELDS.get(_normalize_header(raw))
        if field and field not in mapping:
            mapping[field] = col
    if "name" not in mapping:
        return None
    return mapping


def _ensure_required_columns(mapping: dict[str, int]) -> None:
    required = (("category", "Category"), ("status", "Status"))
    missing = [label for field, label in required if field not in mapping]
    if missing:
        joined = ", ".join(missing)
        raise WorkbookReadError(f"Selected sheet is missing required columns: {joined}")


def _normalize_header(value: object) -> str:
    text = str(value).replace("*", " ").replace("₹", " ")
    text = text.replace("(", " ").replace(")", " ")
    return " ".join(text.replace("\n", " ").strip().lower().split()).rstrip(".")


def _collect_rows(worksheet: Worksheet, header_row: int, columns: dict[str, int]) -> ParsedSheet:
    rows: list[ImportRow] = []
    errors: list[ImportRowError] = []
    seen_codes: set[str] = set()
    total = 0
    last_row = worksheet.max_row or header_row
    for excel_row in range(header_row + 1, last_row + 1):
        values = _read_row(worksheet, excel_row, columns)
        if _is_skippable(values):
            continue
        total += 1
        parsed = _parse_row(excel_row, values, seen_codes)
        if isinstance(parsed, ImportRowError):
            errors.append(parsed)
            continue
        seen_codes.add(parsed.code)
        rows.append(parsed)
    return ParsedSheet(sheet=worksheet.title, total_rows=total, rows=rows, errors=errors)


def _read_row(worksheet: Worksheet, excel_row: int, columns: dict[str, int]) -> dict[str, Any]:
    return {field: worksheet.cell(excel_row, col).value for field, col in columns.items()}


def _is_skippable(values: dict[str, Any]) -> bool:
    if _is_blank(values):
        return True
    name = _clean_text(values.get("name"))
    category = _clean_text(values.get("category"))
    if name and normalize_label(name) in _HINT_NAMES:
        return True
    if category and normalize_label(category) in _HINT_CATEGORIES:
        return True
    return False


def _is_blank(values: dict[str, Any]) -> bool:
    for value in values.values():
        if isinstance(value, (datetime, date)) or _is_number(value):
            return False
        if _clean_text(value):
            return False
    return True


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_row(
    excel_row: int,
    values: dict[str, Any],
    seen_codes: set[str],
) -> ImportRow | ImportRowError:
    identity = _identity(excel_row, values, seen_codes)
    if isinstance(identity, ImportRowError):
        return identity
    optional = _optional_fields(excel_row, values)
    if isinstance(optional, ImportRowError):
        return optional
    try:
        dates = _parse_dates(values)
        cost = _parse_cost(values.get("purchase_cost"))
    except _CellError as exc:
        return ImportRowError(excel_row, exc.field, exc.message)
    return _build_import_row(excel_row, identity, optional, dates, cost)


def _identity(
    excel_row: int,
    values: dict[str, Any],
    seen_codes: set[str],
) -> tuple[str, str, str, str] | ImportRowError:
    name = _required_name(excel_row, values)
    if isinstance(name, ImportRowError):
        return name
    category = _required_category(excel_row, values)
    if isinstance(category, ImportRowError):
        return category
    status = _required_status(excel_row, values)
    if isinstance(status, ImportRowError):
        return status
    code = _required_code(excel_row, values, seen_codes)
    if isinstance(code, ImportRowError):
        return code
    return name, code, category, status


def _required_name(excel_row: int, values: dict[str, Any]) -> str | ImportRowError:
    name = _clean_text(values.get("name"))
    if not name:
        return ImportRowError(excel_row, "name", "Asset name is required")
    if len(name) > 255:
        return ImportRowError(excel_row, "name", "Asset name exceeds the maximum length")
    return name


def _required_category(excel_row: int, values: dict[str, Any]) -> str | ImportRowError:
    text = _clean_text(values.get("category"))
    canonical = TEMPLATE_CATEGORIES.get(normalize_label(text)) if text else None
    if canonical is None:
        return ImportRowError(excel_row, "category", "Category is not a template value")
    return canonical


def _required_status(excel_row: int, values: dict[str, Any]) -> str | ImportRowError:
    text = _clean_text(values.get("status"))
    if not text:
        return AssetStatus.OPERATIONAL.value
    status = STATUS_MAP.get(normalize_label(text))
    if status is None:
        return ImportRowError(excel_row, "status", "Status is not a template value")
    return status


def _required_code(
    excel_row: int,
    values: dict[str, Any],
    seen_codes: set[str],
) -> str | ImportRowError:
    code = _clean_text(values.get("code")) or f"IMP-{excel_row}"
    if len(code) > 100:
        return ImportRowError(excel_row, "code", "Asset code exceeds the maximum length")
    if code in seen_codes:
        return ImportRowError(excel_row, "code", "Asset code is duplicated in the file")
    return code


def _optional_fields(
    excel_row: int,
    values: dict[str, Any],
) -> dict[str, str | None] | ImportRowError:
    cleaned: dict[str, str | None] = {}
    for source, limit, error_field, label in _OPTIONAL_TEXT:
        value = _clean_text(values.get(source))
        if value and len(value) > limit:
            return ImportRowError(excel_row, error_field, f"{label} exceeds the maximum length")
        cleaned[source] = value
    return cleaned


def _parse_dates(values: dict[str, Any]) -> dict[str, date | None]:
    parsed: dict[str, date | None] = {}
    for source, target, label in _DATE_FIELDS:
        parsed[target] = _parse_date(values.get(source), target, label)
    return parsed


def _parse_date(value: Any, field: str, label: str) -> date | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        parsed = _parse_text_date(value.strip())
        if parsed is not None:
            return parsed
    raise _CellError(field, f"{label} is not a valid date")


def _parse_text_date(text: str) -> date | None:
    for fmt in _NUMERIC_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return _parse_named_month(text)


def _parse_named_month(text: str) -> date | None:
    match = re.fullmatch(r"(\d{1,2})-([A-Za-z]+)-(\d{2,4})", text)
    if match is None:
        return None
    month = _MONTHS.get(match.group(2).lower()[:3])
    if month is None:
        return None
    year = int(match.group(3))
    if year < 100:
        year += 2000
    try:
        return date(year, month, int(match.group(1)))
    except ValueError:
        return None


def _parse_cost(value: Any) -> int | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    number = _coerce_cost(value)
    if number < 0 or number > _BIGINT_MAX:
        raise _CellError("purchase_cost", "Purchase cost must be a plain number")
    return number


def _coerce_cost(value: Any) -> int:
    if isinstance(value, str):
        text = value.strip()
        if _PLAIN_NUMBER.fullmatch(text) is None:
            raise _CellError("purchase_cost", "Purchase cost must be a plain number")
        value = float(text) if "." in text else int(text)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value) or not value.is_integer():
            raise _CellError("purchase_cost", "Purchase cost must be a plain number")
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise _CellError("purchase_cost", "Purchase cost must be a plain number")


def _build_import_row(
    excel_row: int,
    identity: tuple[str, str, str, str],
    optional: dict[str, str | None],
    dates: dict[str, date | None],
    cost: int | None,
) -> ImportRow:
    name, code, category_name, status = identity
    return ImportRow(
        excel_row=excel_row,
        name=name,
        code=code,
        category_name=category_name,
        status=status,
        make=optional.get("make"),
        model=optional.get("model"),
        serial_number=optional.get("serial_number"),
        location_text=optional.get("location"),
        landmark_note=optional.get("landmark"),
        purchase_date=dates.get("purchase_date"),
        purchase_cost=cost,
        supplier=optional.get("supplier"),
        invoice_ref=optional.get("invoice_ref"),
        install_date=dates.get("install_date"),
        warranty_expiry=dates.get("warranty_expiry"),
        warranty_terms=optional.get("warranty_terms"),
        description=optional.get("description"),
        quantity=optional.get("quantity"),
    )


def _clean_text(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        text = str(int(value)) if value.is_integer() else str(value).strip()
    elif isinstance(value, int):
        text = str(value)
    else:
        text = str(value).replace("\xa0", " ").strip()
    text = " ".join(text.split())
    return text or None
