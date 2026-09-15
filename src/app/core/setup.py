"""FastAPI application factory, lifespan, and infrastructure setup."""

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from typing import Any

import anyio
import fastapi
from fastapi import APIRouter, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.core.config.app_config import (
    AppSettings,
    DatabaseSettings,
    EnvironmentOption,
)
from app.core.db.postgres.database import (
    close_postgres_connection,
    connect_to_postgres,
)
from app.core.db.redis import redis
from app.core.utils.logger import logger
from app.middleware import setup_middlewares


# -------------- application --------------
async def set_threadpool_tokens(number_of_tokens: int = 100) -> None:
    """Configure the default AnyIO thread pool token limit."""
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = number_of_tokens


async def setup_database(settings: DatabaseSettings) -> None:
    """Set up database connections."""
    # Postgres connection
    if settings.POSTGRES_URI:
        try:
            await connect_to_postgres()
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL: %s", e)
            raise e

    # Redis
    if settings.redis_url and redis is not None:
        try:
            await redis.get_client()
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise e


async def cleanup_redis():
    """Clean up Redis connection."""
    try:
        await redis.close()
    except Exception as e:
        logger.error("Failed to close Redis connection: %s", e)
        raise e


async def cleanup_postgres():
    """Clean up PostgreSQL connection."""
    try:
        await close_postgres_connection()
    except Exception as e:
        logger.error("Failed to close PostgreSQL connection: %s", e)
        raise e


async def cleanup_database() -> None:
    """Clean up database connections with proper error handling."""
    cleanup_tasks = []

    if redis is not None:
        cleanup_tasks.append(cleanup_redis())
    cleanup_tasks.append(cleanup_postgres())

    # Execute cleanup tasks concurrently
    results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    # Log any cleanup failures
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Cleanup task %s failed: %s", i, result)


def lifespan_factory(
    settings: DatabaseSettings | AppSettings,
) -> Callable[[FastAPI], _AsyncGeneratorContextManager[Any]]:
    """Create a lifespan async context manager for a FastAPI app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        from asyncio import Event

        initialization_complete = Event()
        app.state.initialization_complete = initialization_complete

        await set_threadpool_tokens()

        try:
            # Skip external service setup in test mode
            if settings.ENVIRONMENT == EnvironmentOption.TEST:
                logger.info("🔄 Skipping external service setup in test mode")
                initialization_complete.set()
                yield
                return

            # Set up database connections
            await setup_database(settings)

            background_tasks: list[asyncio.Task] = []
            if (
                isinstance(settings, AppSettings)
                and settings.WOM_SCHEDULER_ENABLED
                and settings.WOM_EMBEDDED_SCHEDULER
            ):
                from app.workers.schedulers.scheduler_worker import run_scheduler_loop

                background_tasks.append(asyncio.create_task(run_scheduler_loop()))
                logger.info("Embedded scheduler loop started")

            webhook_task: asyncio.Task | None = None
            if isinstance(settings, AppSettings) and settings.WOM_EMBEDDED_WEBHOOK_WORKER:
                from app.workers.schedulers.webhook_delivery_worker import (
                    webhook_delivery_worker,
                )

                webhook_task = asyncio.create_task(webhook_delivery_worker.run_forever())
                background_tasks.append(webhook_task)
                logger.info("Embedded webhook delivery worker started")

            # Other initializations...
            initialization_complete.set()

            yield

            for task in background_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            if isinstance(settings, AppSettings) and settings.WOM_EMBEDDED_WEBHOOK_WORKER:
                from app.workers.schedulers.webhook_delivery_worker import (
                    webhook_delivery_worker,
                )

                await webhook_delivery_worker.stop()

        finally:
            # Cleanup services in reverse order
            if settings.ENVIRONMENT != EnvironmentOption.TEST:
                # Clean up database connections
                await cleanup_database()

    return lifespan


# Function to extract auth roles from route
def extract_route_auth_roles(route) -> list[str]:
    """Extract authentication roles required for a route.

    Parameters
    ----------
    route : APIRoute
        The FastAPI route to analyze

    Returns:
    -------
    list[str]
        List of role names required for this route

    """
    # Default roles if we can't determine specifics
    roles = False

    try:
        if hasattr(route, "dependencies"):
            for dep in route.dependencies:
                # Check if it's a Security dependency
                if hasattr(dep, "dependency"):
                    if hasattr(dep.dependency, "allowed_roles"):
                        return dep.dependency.allowed_roles
    except Exception as e:
        logger.error("Error extracting auth roles: %s", e)

    return roles


# Function to generate krakend.json configuration
def generate_krakend_config(app: FastAPI, host_url: str) -> dict[str, list[dict]]:
    """Generate a KrakenD configuration from the FastAPI routes.

    This function scans the routes defined in the FastAPI application and generates
    a KrakenD gateway configuration based on these routes.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application whose routes will be converted to KrakenD endpoints
    host_url : str
        The backend service URL that KrakenD will use

    Returns:
    -------
    dict[str, list[dict]]
        A dictionary containing the KrakenD configuration with endpoints

    """
    endpoints = []

    for route in app.routes:
        # Skip endpoints that don't have a path or are special routes (like docs)
        if (
            not hasattr(route, "path")
            or route.path
            in [
                "/docs",
                "/redoc",
                "/openapi.json",
                "/krakend.json",
                "/docs/oauth2-redirect",
                "/docs/oauth2-callback",
            ]
            or route.path.endswith("/health")
        ):
            continue

        # Extract path and methods
        path = route.path
        if not hasattr(route, "methods"):
            continue

        # Extract headers specific to this route
        route_headers = [
            "Authorization",
            "x-api-key",
            "x-tenant-id",
            "x-project-id",
            "x-subject-user-id",
            "lan",
            "city",
            "state",
            "country",
            "ipaddress",
            "latitude",
            "longitude",
            "platform",
            "version",
        ]

        # Extract auth roles required for this route
        auth_roles = extract_route_auth_roles(route)

        for method in route.methods:
            # Create endpoint configuration
            endpoint_config = {
                "endpoint": path,
                "method": method,
                "input_query_strings": ["*"],
                "input_headers": route_headers,
                "backend": [
                    {
                        "url_pattern": path,
                        "encoding": "no-op",
                        "host": [host_url],
                        "method": method,
                    }
                ],
                "extra_config": {"plugin/auth-custom": {"auth": auth_roles}},
                "output_encoding": "NoTransformRender",
            }

            endpoints.append(endpoint_config)

    return {"endpoints": endpoints}


# -------------- application --------------
def create_application(
    router: APIRouter,
    settings: AppSettings,
    **kwargs: Any,
) -> FastAPI:
    """Create and configure a FastAPI application based on the provided settings.

    This function initializes a FastAPI application and configures it with various settings
    and handlers based on the type of the `settings` object provided.

    Parameters
    ----------
    router : APIRouter
        The APIRouter object containing the routes to be included in the FastAPI application.

    settings
        An instance representing the settings for configuring the FastAPI application.
        It determines the configuration applied:

        - AppSettings: Configures basic app metadata like name, description, contact, and
          license info.

    **kwargs
        Additional keyword arguments passed directly to the FastAPI constructor.

    Returns:
    -------
    FastAPI
        A fully configured FastAPI application instance.

    The function configures the FastAPI application with different features and behaviors
    based on the provided settings. It includes setting up database connections, Redis
    pools for caching, queue, and rate limiting, client-side caching, and customizing
    the API documentation based on the environment settings.

    """
    # --- before creating application ---
    if isinstance(settings, AppSettings):
        to_update = {
            "title": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "license_info": {"name": settings.LICENSE_NAME} if settings.LICENSE_NAME else None,
        }

        # Only add contact info if both name and email are valid
        if settings.CONTACT_NAME and settings.CONTACT_EMAIL and "@" in settings.CONTACT_EMAIL:
            to_update["contact"] = {"name": settings.CONTACT_NAME, "email": settings.CONTACT_EMAIL}

        # Remove None values
        to_update = {k: v for k, v in to_update.items() if v is not None}
        kwargs.update(to_update)

    # Only disable docs in production environment
    if settings.ENVIRONMENT == EnvironmentOption.PRODUCTION:
        kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

    lifespan = lifespan_factory(settings)

    application = FastAPI(lifespan=lifespan, **kwargs)

    application.include_router(router)

    # Register exception handlers
    from app.core.exception_handlers import register_exception_handlers

    register_exception_handlers(application)

    # Setup middleware
    setup_middlewares(application)

    # Add custom documentation routes for non-production environments
    if settings.ENVIRONMENT and settings.ENVIRONMENT != EnvironmentOption.PRODUCTION:
        docs_router = APIRouter()

        @docs_router.get("/docs", include_in_schema=False)
        async def get_swagger_documentation() -> fastapi.responses.HTMLResponse:
            return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

        @docs_router.get("/redoc", include_in_schema=False)
        async def get_redoc_documentation() -> fastapi.responses.HTMLResponse:
            return get_redoc_html(openapi_url="/openapi.json", title="docs")

        @docs_router.get("/openapi.json", include_in_schema=False)
        async def openapi() -> dict[str, Any]:
            out: dict = get_openapi(
                title=application.title,
                version=application.version,
                routes=application.routes,
            )
            return out

        @docs_router.get("/krakend.json", include_in_schema=False)
        async def krakend() -> dict[str, Any]:
            # Get host URL from configuration, or use default
            host_url = (
                getattr(settings, "SERVICE_URL", "http://host:3006")
                if hasattr(settings, "SERVICE_URL")
                else "http://host:3006"
            )
            return generate_krakend_config(application, host_url)

        application.include_router(docs_router)

    return application
