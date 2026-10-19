"""Unit tests for HoA company list helpers."""

from app.business.services.hoa_service import _active_companies_only


def test_active_companies_only_keeps_active_rows():
    """Active filter keeps active companies regardless of casing."""
    companies = [
        {"id": "1", "name": "Active Co", "status": "active"},
        {"id": "2", "name": "Removed Co", "status": "deleted"},
        {"id": "3", "name": "Inactive Co", "status": "inactive"},
        {"id": "4", "name": "Legacy Active", "status": "Active"},
    ]
    assert _active_companies_only(companies) == [
        {"id": "1", "name": "Active Co", "status": "active"},
        {"id": "4", "name": "Legacy Active", "status": "Active"},
    ]
