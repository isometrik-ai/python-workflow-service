"""Shared pytest fixtures and environment setup for the test suite."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

test_env_path = Path(__file__).parent.parent / ".env.test"
if test_env_path.exists():
    load_dotenv(test_env_path, override=True)
else:
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault(
        "POSTGRES_URI",
        "work_order_service",
    )


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, Any, None]:
    """FastAPI test client without external Postgres/Redis startup."""
    from app.api import router
    from app.core.exception_handlers import register_exception_handlers
    from app.middleware.setup import setup_middlewares

    test_app = FastAPI(title="Test API", version="1.0.0")
    setup_middlewares(test_app)
    test_app.include_router(router)
    register_exception_handlers(test_app)

    with TestClient(test_app) as test_client:
        yield test_client
