"""Tests for asset workbook parsing and import."""

from datetime import date, datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openpyxl import Workbook
from sqlalchemy.exc import IntegrityError

from app.business.services.asset_import_service import (
    MAX_IMPORT_BYTES,
    AssetImportService,
)
from app.business.services.asset_workbook import parse_asset_workbook
from app.core.exceptions.http_exceptions import ValidationException

PIOUS_HEADERS = [
    "Asset Name *",
    "Asset Code / Tag No.",
    "Category *",
    "Make",
    "Model",
    "Serial Number",
    "Status *",
    "Location *",
    "Landmark",
    "Purchase Date",
    "Purchase Cost (₹)",
    "Supplier / Vendor",
    "Invoice / PO No.",
    "Installation Date",
    "Warranty End",
    "Warranty / AMC Details",
    "Notes",
]

FIRE_HEADERS = [
    "SR/NO.",
    "Asset Name *",
    "Asset Code / Tag No.",
    "Quantity",
    "Category *",
    "Make / Brand",
    "Model",
    "Serial Number",
    "Status *",
    "Location *",
    "Landmark",
    "Purchase Date",
    "Purchase Cost (₹)",
    "Supplier / Vendor",
    "Invoice / PO No.",
    "Installation Date",
    "Warranty End",
    "Warranty / AMC Details",
    "Notes",
]


def _save(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _workbook(title: str, rows: list[list]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = title
    for row_index, row in enumerate(rows, start=1):
        for column, value in enumerate(row, start=1):
            if value is not None:
                worksheet.cell(row_index, column, value)
    return _save(workbook)


def _pious_row(**overrides) -> list:
    values = {
        "name": "Pump A",
        "code": "P-1",
        "category": "Electrical",
        "make": "Omega",
        "model": "UW2",
        "serial_number": "SN1",
        "status": "Working",
        "location": "Lt Room",
        "landmark": "Tower-1 Basement",
        "purchase_date": date(2024, 3, 15),
        "purchase_cost": 450000,
        "supplier": "Acme HVAC Supplies",
        "invoice_ref": "INV-2024-331",
        "install_date": date(2024, 4, 1),
        "warranty_expiry": date(2027, 4, 1),
        "warranty_terms": "3 yrs parts & labour",
        "description": "Capacity 5 TR",
    }
    values.update(overrides)
    return [
        values[key]
        for key in (
            "name",
            "code",
            "category",
            "make",
            "model",
            "serial_number",
            "status",
            "location",
            "landmark",
            "purchase_date",
            "purchase_cost",
            "supplier",
            "invoice_ref",
            "install_date",
            "warranty_expiry",
            "warranty_terms",
            "description",
        )
    ]


class _Nested:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class ImportHarness:
    """Run the import service with collaborators replaced."""

    def __init__(self):
        """Store stand-in data for one import run."""
        self.payloads: list[dict] = []
        self.created_categories: list[str] = []
        self.vendor_names: list[str] = []
        self.codes: set[str] = set()
        self.existing_categories: list[dict] = []
        self.local_vendors: list[dict] = []
        self.search_result: dict = {"total": 0, "data": []}
        self.create_error: Exception | None = None
        self.insert_error = False
        self.db = MagicMock()
        self.db.begin_nested.return_value = _Nested()

    async def run(self, content: bytes, *, filename: str = "assets.xlsx", sheet: str | None = None):
        """Import one workbook with the stand-in collaborators."""
        service = AssetImportService(self.db, "tenant123", "project123")
        with (
            patch("app.business.services.asset_import_service.crud_assets") as assets,
            patch("app.business.services.asset_import_service.crud_asset_categories") as categories,
            patch.object(
                service.vendors,
                "list_local_vendors",
                new=AsyncMock(return_value=self.local_vendors),
            ),
            patch.object(service.vendors, "search", new=AsyncMock(return_value=self.search_result)),
            patch.object(service.vendors, "create", new=AsyncMock(side_effect=self._create_vendor)),
        ):
            assets.list_codes = AsyncMock(return_value=set(self.codes))
            assets.release_deleted_codes = AsyncMock()
            assets.create_many = AsyncMock(side_effect=self._create_assets)
            categories.list_active = AsyncMock(return_value=list(self.existing_categories))
            categories.get_active_by_label = AsyncMock(return_value=None)
            categories.create = AsyncMock(side_effect=self._create_category)
            return await service.import_workbook(content, filename=filename, sheet_name=sheet)

    async def _create_assets(self, *_args, **kwargs):
        if self.insert_error:
            raise IntegrityError("insert", {}, Exception("duplicate"))
        self.payloads.extend(kwargs["items"])
        return [item["code"] for item in kwargs["items"]]

    async def _create_category(self, *_args, **kwargs):
        self.created_categories.append(kwargs["name"])
        return {"id": f"cat-{len(self.created_categories)}", "name": kwargs["name"]}

    async def _create_vendor(self, name: str):
        if self.create_error:
            raise self.create_error
        self.vendor_names.append(name)
        return {"id": f"ven-{len(self.vendor_names)}", "name": name}


def test_parse_pious_layout_maps_columns_and_generates_blank_codes():
    """The 17-column register maps onto asset fields and fills a missing code."""
    content = _workbook("Assets", [PIOUS_HEADERS, _pious_row(code=None, status=None)])
    parsed = parse_asset_workbook(content, None)

    assert parsed.sheet == "Assets"
    assert parsed.total_rows == 1
    assert parsed.errors == []
    row = parsed.rows[0]
    assert row.excel_row == 2
    assert row.code == "IMP-2"
    assert row.category_name == "Electrical"
    assert row.status == "operational"
    assert row.make == "Omega"
    assert row.location_text == "Lt Room"
    assert row.landmark_note == "Tower-1 Basement"
    assert row.purchase_date == date(2024, 3, 15)
    assert row.purchase_cost == 450000
    assert row.invoice_ref == "INV-2024-331"
    assert row.warranty_expiry == date(2027, 4, 1)
    assert row.description == "Capacity 5 TR"


def test_parse_fire_layout_skips_hint_row_and_keeps_quantity():
    """The wider fire register ignores the hint row and keeps quantity text."""
    hint = [
        None,
        "What you call it",
        "Code on the asset",
        None,
        "Pick from list",
        None,
        None,
        None,
        None,
        "e.g. Tower A – Ground floor",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "e.g. 3 yrs parts & labour",
        "e.g. Capacity 5 TR",
    ]
    data = [
        1,
        "Jockey Pump",
        None,
        "12 No's",
        "Fire Safety",
        "Kirloskar",
        "KCIL",
        12955220120,
        "Under Maintenance",
        "Basement-1",
        "Basement-1",
        "15-Mar-2024",
        2128800,
        "Goel & Associates",
        "PHWOJ/00080/23",
        datetime(2023, 3, 31),
        datetime(2025, 10, 19),
        "AMC",
        "Loop panel",
    ]
    content = _workbook("Assets", [FIRE_HEADERS, hint, data])
    parsed = parse_asset_workbook(content, None)

    assert parsed.total_rows == 1
    row = parsed.rows[0]
    assert row.excel_row == 3
    assert row.code == "IMP-3"
    assert row.quantity == "12 No's"
    assert row.make == "Kirloskar"
    assert row.serial_number == "12955220120"
    assert row.status == "under_repair"
    assert row.purchase_date == date(2024, 3, 15)
    assert row.category_name == "Fire Safety"


def test_parse_finds_header_below_a_title_row():
    """Tower sheets keep the header on row 2 and data after the hint row."""
    content = _workbook(
        "Tower-01",
        [
            ["Tower register"],
            FIRE_HEADERS,
            [None, "What you call it", None, None, "Pick from list"],
            [
                1,
                "Hydrant",
                None,
                1,
                "Fire Safety",
                "Safe Guard",
                None,
                None,
                "Not Working",
                "Tower-1",
            ],
        ],
    )
    parsed = parse_asset_workbook(content, "tower-01")

    assert parsed.sheet == "Tower-01"
    assert parsed.total_rows == 1
    assert parsed.rows[0].excel_row == 4
    assert parsed.rows[0].code == "IMP-4"
    assert parsed.rows[0].status == "faulty"
    assert parsed.rows[0].quantity == "1"


def test_parse_rejects_shifted_and_invalid_cells_and_duplicate_codes():
    """Unknown categories, statuses, costs, dates, and repeated codes fail the row."""
    content = _workbook(
        "Assets",
        [
            PIOUS_HEADERS,
            _pious_row(name="Good", code="SAME"),
            _pious_row(name="Shifted", category="384No's"),
            _pious_row(name="Bad status", status="E22ULL000020"),
            _pious_row(name="Bad cost", purchase_cost="₹4,50,000"),
            _pious_row(name="Bad date", purchase_date="yesterday"),
            _pious_row(name="Duplicate", code="SAME"),
            _pious_row(name="Retired", status="Retired", code="R-1"),
        ],
    )
    parsed = parse_asset_workbook(content, None)

    assert parsed.total_rows == 7
    assert [row.name for row in parsed.rows] == ["Good", "Retired"]
    assert parsed.rows[1].status == "decommissioned"
    messages = {error.field: error.message for error in parsed.errors}
    assert messages["category"] == "Category is not a template value"
    assert messages["status"] == "Status is not a template value"
    assert messages["purchase_cost"] == "Purchase cost must be a plain number"
    assert messages["purchase_date"] == "Purchase date is not a valid date"
    assert messages["code"] == "Asset code is duplicated in the file"


def test_parse_copies_merged_purchase_cost_onto_each_row():
    """A merged cost cell is applied to every row in the merge."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Assets"
    for column, header in enumerate(PIOUS_HEADERS, start=1):
        worksheet.cell(1, column, header)
    worksheet.cell(2, 1, "Pump A")
    worksheet.cell(2, 3, "Electrical")
    worksheet.cell(2, 7, "Working")
    worksheet.cell(2, 11, 1000)
    worksheet.cell(3, 1, "Pump B")
    worksheet.cell(3, 3, "Electrical")
    worksheet.cell(3, 7, "Working")
    worksheet.merge_cells("K2:K3")

    parsed = parse_asset_workbook(_save(workbook), None)

    assert [row.purchase_cost for row in parsed.rows] == [1000, 1000]
    assert [row.code for row in parsed.rows] == ["IMP-2", "IMP-3"]


def test_parse_requires_the_assets_sheet_unless_a_sheet_is_named():
    """The default sheet is Assets, and a workbook without that sheet is rejected."""
    content = _workbook("Notes", [["Hello"]])

    with pytest.raises(Exception, match="Sheet 'Assets' was not found") as caught:
        parse_asset_workbook(content, None)

    from app.business.services.asset_workbook import WorkbookReadError

    assert isinstance(caught.value, WorkbookReadError)


@pytest.mark.asyncio
async def test_import_creates_category_and_vendor_once_for_accepted_rows():
    """Accepted rows share one new category and one new vendor. Rejected rows do not."""
    hint = [None, "What you call it", None, None, "Pick from list"]
    pump_a = [
        1,
        "Pump A",
        None,
        "2 No's",
        "Electrical",
        "Omega",
        None,
        None,
        "Working",
        "Lt Room",
        None,
        None,
        450000,
        "Kirloskar",
        "INV-1",
        None,
        None,
        None,
        "Note",
    ]
    pump_b = [
        2,
        "Pump B",
        None,
        None,
        "electrical",
        None,
        None,
        None,
        None,
        "Lt Room",
        None,
        None,
        None,
        "kirloskar",
        None,
        None,
        None,
        None,
        None,
    ]
    shifted = [
        3,
        "Shifted",
        None,
        None,
        "384No's",
        None,
        None,
        None,
        "Working",
        "Lt Room",
        None,
        None,
        None,
        "Should Not Create",
        None,
        None,
        None,
        None,
        None,
    ]
    content = _workbook("Assets", [FIRE_HEADERS, hint, pump_a, pump_b, shifted])
    harness = ImportHarness()

    result = await harness.run(content)

    assert result["created"] == 2
    assert result["failed"] == 1
    assert result["created_codes"] == ["IMP-3", "IMP-4"]
    assert result["errors"][0]["field"] == "category"
    assert harness.created_categories == ["Electrical"]
    assert harness.vendor_names == ["Kirloskar"]
    assert result["vendors_created"] == [{"name": "Kirloskar", "id": "ven-1"}]
    assert harness.payloads[0]["currency"] == "INR"
    assert harness.payloads[0]["custom_field_values"] == {"quantity": "2 No's"}
    assert harness.payloads[0]["purchase_cost"] == 450000
    assert harness.payloads[0]["supplier"] == "Kirloskar"
    assert harness.payloads[0]["supplier_vendor_id"] == "ven-1"
    assert harness.payloads[1]["status"] == "operational"
    assert harness.payloads[1]["supplier_vendor_id"] == "ven-1"
    assert harness.payloads[0]["category_id"] == harness.payloads[1]["category_id"] == "cat-1"


@pytest.mark.asyncio
async def test_import_reuses_existing_category_and_local_vendor():
    """A category and vendor that already exist are linked and not created again."""
    content = _workbook("Assets", [PIOUS_HEADERS, _pious_row(supplier="kirloskar")])
    harness = ImportHarness()
    harness.existing_categories = [{"id": "cat-existing", "name": "electrical"}]
    harness.local_vendors = [{"id": "ven-1", "name": "Kirloskar"}]

    result = await harness.run(content)

    assert result["created"] == 1
    assert harness.created_categories == []
    assert harness.vendor_names == []
    assert result["vendors_matched"] == [{"name": "Kirloskar", "id": "ven-1"}]
    assert harness.payloads[0]["category_id"] == "cat-existing"
    assert harness.payloads[0]["supplier"] == "Kirloskar"
    assert harness.payloads[0]["supplier_vendor_id"] == "ven-1"


@pytest.mark.asyncio
async def test_import_keeps_the_oldest_category_when_names_are_duplicated():
    """A second category with the same name is ignored and no new category is created."""
    content = _workbook("Assets", [PIOUS_HEADERS, _pious_row()])
    harness = ImportHarness()
    harness.existing_categories = [
        {"id": "cat-old", "name": "Electrical"},
        {"id": "cat-new", "name": "Electrical"},
    ]

    result = await harness.run(content)

    assert result["created"] == 1
    assert harness.created_categories == []
    assert harness.payloads[0]["category_id"] == "cat-old"


@pytest.mark.asyncio
async def test_import_matches_an_exact_house_of_apps_vendor():
    """House of Apps is used only when the full supplier name matches."""
    content = _workbook("Assets", [PIOUS_HEADERS, _pious_row(supplier="Kirloskar")])
    harness = ImportHarness()
    harness.existing_categories = [{"id": "cat-existing", "name": "Electrical"}]
    harness.search_result = {"total": 1, "data": [{"id": "hoa-1", "name": "Kirloskar"}]}

    result = await harness.run(content)

    assert harness.vendor_names == []
    assert result["vendors_matched"] == [{"name": "Kirloskar", "id": "hoa-1"}]
    assert harness.payloads[0]["supplier_vendor_id"] == "hoa-1"


@pytest.mark.asyncio
async def test_import_creates_vendor_when_search_is_only_a_partial_name():
    """A longer company name that merely contains the supplier does not count as a match."""
    content = _workbook("Assets", [PIOUS_HEADERS, _pious_row(supplier="Kirloskar")])
    harness = ImportHarness()
    harness.existing_categories = [{"id": "cat-existing", "name": "Electrical"}]
    harness.search_result = {"total": 1, "data": [{"id": "hoa-2", "name": "Kirloskar Pumps"}]}

    result = await harness.run(content)

    assert harness.vendor_names == ["Kirloskar"]
    assert result["vendors_created"][0]["name"] == "Kirloskar"
    assert result["vendors_matched"] == []


@pytest.mark.asyncio
async def test_import_keeps_the_asset_when_vendor_create_fails():
    """A vendor create failure leaves the supplier name on the asset and lists it as unlinked."""
    content = _workbook("Assets", [PIOUS_HEADERS, _pious_row(supplier="Omega")])
    harness = ImportHarness()
    harness.existing_categories = [{"id": "cat-existing", "name": "Electrical"}]
    harness.create_error = RuntimeError("house of apps unavailable")

    result = await harness.run(content)

    assert result["created"] == 1
    assert result["vendors_unlinked"] == ["Omega"]
    assert result["vendors_created"] == []
    assert harness.payloads[0]["supplier"] == "Omega"
    assert harness.payloads[0]["supplier_vendor_id"] is None


@pytest.mark.asyncio
async def test_import_rejects_a_code_that_already_exists_for_the_project():
    """An existing project code fails that row and does not create its supplier."""
    content = _workbook(
        "Assets",
        [PIOUS_HEADERS, _pious_row(code="CH-001", supplier="New Supplier")],
    )
    harness = ImportHarness()
    harness.codes = {"CH-001"}

    result = await harness.run(content)

    assert result["created"] == 0
    assert result["failed"] == 1
    assert result["errors"][0]["message"] == "Asset code already exists for the project"
    assert harness.vendor_names == []
    assert harness.payloads == []


@pytest.mark.asyncio
async def test_import_reports_a_database_duplicate_without_failing_the_file():
    """A unique-constraint failure on insert becomes a row error."""
    content = _workbook("Assets", [PIOUS_HEADERS, _pious_row()])
    harness = ImportHarness()
    harness.existing_categories = [{"id": "cat-existing", "name": "Electrical"}]
    harness.insert_error = True

    result = await harness.run(content)

    assert result["created"] == 0
    assert result["failed"] == 1
    assert result["errors"][0]["field"] == "code"


@pytest.mark.asyncio
async def test_import_rejects_a_workbook_that_cannot_be_read():
    """File type, emptiness, size, and a missing sheet fail the request."""
    service = AssetImportService(MagicMock(), "tenant", "project")

    with pytest.raises(ValidationException) as non_xlsx:
        await service.import_workbook(b"name", filename="assets.csv", sheet_name=None)
    assert non_xlsx.value.status_code == 400
    assert "xlsx" in non_xlsx.value.params["message"]

    with pytest.raises(ValidationException) as empty:
        await service.import_workbook(b"", filename="assets.xlsx", sheet_name=None)
    assert "empty" in empty.value.params["message"]

    oversized = b"x" * (MAX_IMPORT_BYTES + 1)
    with pytest.raises(ValidationException) as oversized_file:
        await service.import_workbook(oversized, filename="assets.xlsx", sheet_name=None)
    assert "15 MB" in oversized_file.value.params["message"]

    with pytest.raises(ValidationException) as invalid:
        await service.import_workbook(b"not-a-zip", filename="assets.xlsx", sheet_name=None)
    assert "valid .xlsx" in invalid.value.params["message"]

    missing = _workbook("Notes", [["Hello"]])
    with pytest.raises(ValidationException) as missing_sheet:
        await service.import_workbook(missing, filename="assets.xlsx", sheet_name=None)
    assert "Assets" in missing_sheet.value.params["message"]
