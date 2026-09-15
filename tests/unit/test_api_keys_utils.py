"""Tests for api keys utils."""

from app.core.utils.api_keys import generate_api_key, hash_api_key
from app.crud.crud_api_keys import crud_api_keys


def test_hash_api_key_is_deterministic():
    """Test hash api key is deterministic."""
    raw = "test-api-key-value-12345"
    assert hash_api_key(raw) == hash_api_key(raw)


def test_generate_api_key_returns_prefix_and_hash():
    """Test generate api key returns prefix and hash."""
    raw, key_hash, prefix = generate_api_key()
    assert len(raw) > 16
    assert key_hash == hash_api_key(raw)
    assert raw.startswith(prefix)


def test_crud_api_key_new_id_uses_work_order_prefix_pattern():
    """Test crud api key new id uses work order prefix pattern."""
    key_id = crud_api_keys.new_id()
    assert key_id.startswith("api_key_")
    assert len(key_id) == len("api_key_") + 12
