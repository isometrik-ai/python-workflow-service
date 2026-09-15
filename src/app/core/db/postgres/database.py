"""PostgreSQL async engine, sessions, and transaction lifecycle.

Session entry point
-------------------
* :func:`async_get_db_session` — primary async context manager for database work:

  - Workers, cron, moderation: ``async with async_get_db_session() as db:``

  Always use ``async with`` (never ``async for db in async_get_db_session()``).

* :func:`async_get_db` — FastAPI dependency (wraps :func:`async_get_db_session`):

  - API routes: ``Depends(async_get_db)``

* :func:`async_get_db_manual` — rare cases that need explicit commit/rollback.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config.app_config import EnvironmentOption, settings
from app.core.utils.logger import logger


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for ORM models."""


def _uses_transaction_pooler(uri: str) -> bool:
    """Return True when the URI targets a PgBouncer-style transaction pooler."""
    lowered = uri.lower()
    return "pooler" in lowered or ":6543/" in lowered or ":6543?" in lowered


def _requires_pooler_safe_connect_args() -> bool:
    """Return True when prepared statements must be disabled for the DB endpoint."""
    if settings.POSTGRES_STATEMENT_CACHE_SIZE is not None:
        return settings.POSTGRES_STATEMENT_CACHE_SIZE == 0
    return _uses_transaction_pooler(settings.POSTGRES_URI)


def postgres_engine_kwargs() -> dict[str, object]:
    """Build PostgreSQL engine kwargs for Supabase/PgBouncer transaction poolers."""
    if not _requires_pooler_safe_connect_args():
        if settings.POSTGRES_STATEMENT_CACHE_SIZE is not None:
            return {
                "connect_args": {
                    "statement_cache_size": settings.POSTGRES_STATEMENT_CACHE_SIZE,
                },
            }
        return {}

    return {
        "poolclass": NullPool,
        "connect_args": {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        },
    }


def _create_async_engine():
    """Create async engine with appropriate configuration based on environment."""
    if settings.ENVIRONMENT == EnvironmentOption.TEST:
        # SQLite configuration for tests
        return create_async_engine(
            settings.POSTGRES_URI,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )

    # PostgreSQL configuration for other environments
    engine_kwargs: dict[str, object] = {
        "echo": False,
        "future": True,
        "pool_pre_ping": True,
        **postgres_engine_kwargs(),
    }
    if "poolclass" not in engine_kwargs:
        engine_kwargs.update(
            {
                "pool_size": 20,
                "max_overflow": 30,
                "pool_recycle": 3600,
                "pool_timeout": 30,
            }
        )

    return create_async_engine(
        settings.POSTGRES_URI,
        **engine_kwargs,
    )


# Create async engine with appropriate configuration
async_engine = _create_async_engine()

# Create async session maker
async_session_maker = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Queue async work on ``session.info`` so it runs only after a successful commit.
# Avoids consumers reading stale rows when Kafka delivers before the API transaction commits.
AFTER_COMMIT_CALLBACKS_KEY = "work_order_service_after_commit_callbacks"


def schedule_after_commit(
    session: AsyncSession,
    callback: Callable[[], Awaitable[Any]],
) -> None:
    """Run ``callback`` after this session's transaction commits successfully.

    Used for side effects (e.g. Kafka) that must observe committed data in other sessions.
    """
    pending: list[Callable[[], Awaitable[Any]]] = session.info.setdefault(
        AFTER_COMMIT_CALLBACKS_KEY,
        [],
    )
    pending.append(callback)


def discard_after_commit_callbacks(session: AsyncSession) -> None:
    """Drop pending after-commit callbacks (e.g. after rollback)."""
    session.info.pop(AFTER_COMMIT_CALLBACKS_KEY, None)


async def run_after_commit_callbacks(session: AsyncSession) -> None:
    """Execute and clear all after-commit callbacks for this session."""
    callbacks = session.info.pop(AFTER_COMMIT_CALLBACKS_KEY, None)
    if not callbacks:
        return
    for cb in callbacks:
        await cb()


@asynccontextmanager
async def async_get_db_session() -> AsyncGenerator[AsyncSession]:
    """Database session with commit, rollback, and after-commit hooks.

    Primary entry point for database work. Use in workers and services:
    ``async with async_get_db_session() as db:``

    ``__aexit__`` commits and runs :func:`run_after_commit_callbacks` on success,
    or rolls back and clears pending callbacks on error (including early ``return``).

    Important: registering :func:`schedule_after_commit` and then exiting the
    ``async for`` body with ``return`` or ``break`` raises ``GeneratorExit`` at
    the yield and **skips**
    the generator code after ``yield``. If you manually call
    :meth:`~sqlalchemy.ext.asyncio.AsyncSession.commit` inside the loop, you
    **must** also await :func:`run_after_commit_callbacks` on that same session
    so those callbacks fire.

    Yields:
    ------
    AsyncSession
        An async session object with automatic transaction management

    """
    session = async_session_maker()
    try:
        yield session
        # If we reach here, no exception occurred - commit the transaction
        await session.commit()
        await run_after_commit_callbacks(session)
    except Exception:
        # If any exception occurred, rollback the transaction
        await session.rollback()
        discard_after_commit_callbacks(session)
        raise  # Re-raise the exception so it can be handled by the endpoint
    finally:
        await session.close()


async def async_get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency wrapping :func:`async_get_db_session`.

    Use in API routes: ``db: AsyncSession = Depends(async_get_db)``

    FastAPI consumes this async generator directly. Do not decorate with
    ``@asynccontextmanager`` — that breaks ``Depends()`` (injects a context manager
    object instead of :class:`AsyncSession`).
    """
    async with async_get_db_session() as session:
        yield session


@asynccontextmanager
async def async_get_db_manual() -> AsyncGenerator[AsyncSession]:
    """Get an async database session with manual transaction control.

    Use this when you need fine-grained control over transactions,
    such as multiple commits within a single endpoint or custom rollback logic.

    Note: You must manually handle commit/rollback with this session.

    Yields:
    ------
    AsyncSession
        An async session object requiring manual transaction management

    """
    session = async_session_maker()
    try:
        yield session
        # No automatic commit - caller must handle transactions
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def ensure_db_schema(conn) -> None:
    """Create the configured PostgreSQL schema if it does not exist."""
    schema = settings.POSTGRES_SCHEMA
    await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))


async def connect_to_postgres():
    """Initialize PostgreSQL schema and create ORM tables."""
    import app.models  # noqa: F401  # register mappers before create_all

    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT pg_advisory_xact_lock(hashtext('schema_setup'))"))

            await ensure_db_schema(conn)

            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ PostgreSQL connection established and created tables successfully!")
    except Exception as e:
        logger.error("⚠️ Error connecting to PostgreSQL: %s", e)
        raise


async def close_postgres_connection():
    """Dispose of the async PostgreSQL engine and close all connections."""
    try:
        await async_engine.dispose()
        logger.info("✅ PostgreSQL connection closed!")
    except Exception as e:
        logger.error("⚠️ Error closing PostgreSQL connection: %s", e)
