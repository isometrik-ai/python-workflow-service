"""Unit tests for contract vendor selection rules."""

from app.business.services.vendor_service import _active_vendors_only


def test_active_vendors_only_excludes_stale_local_crm_ids():
    """Asset-derived CRM ids are excluded when they are not workflow-local ids."""
    vendors = [
        {"id": "crm-uuid-1", "name": "Removed From CRM", "source": "local"},
        {"id": "ven-1", "name": "Seeded Supplier", "source": "local"},
    ]
    assert _active_vendors_only(vendors) == [
        {"id": "ven-1", "name": "Seeded Supplier", "source": "local"},
    ]


def test_active_vendors_only_keeps_active_crm_only():
    """Only active HoA vendors and ven-* local seeds remain selectable."""
    vendors = [
        {"id": "1", "name": "Active Co", "status": "active", "source": "houseofapps"},
        {"id": "2", "name": "Deleted Co", "status": "deleted", "source": "houseofapps"},
        {"id": "3", "name": "Inactive Co", "status": "inactive", "source": "houseofapps"},
        {"id": "asset-crm-uuid", "name": "Asset Supplier", "source": "local"},
        {"id": "ven-2", "name": "Seeded", "source": "local"},
    ]
    assert _active_vendors_only(vendors) == [
        {"id": "1", "name": "Active Co", "status": "active", "source": "houseofapps"},
        {"id": "ven-2", "name": "Seeded", "source": "local"},
    ]
