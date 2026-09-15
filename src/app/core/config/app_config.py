"""Application configuration loaded from environment variables."""

import json
import os
from enum import Enum

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from starlette.config import Config

if os.environ.get("ENVIRONMENT") != "test":
    load_dotenv()

config = Config()


class EnvironmentOption(str, Enum):
    """Supported deployment environment names."""

    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class AppSettings(BaseSettings):
    """General application metadata and runtime settings."""

    APP_NAME: str = config("APP_NAME", default="Work Order Service")
    APP_DESCRIPTION: str | None = config(
        "APP_DESCRIPTION",
        default="FastAPI work-order service",
    )
    APP_VERSION: str | None = config("APP_VERSION", default="1.0.0")
    PORT: str = config("PORT", default="8080")
    RELOAD: str = config("RELOAD", default="false")
    LOG_LEVEL: str | None = config("LOG_LEVEL", default="INFO")
    LICENSE_NAME: str | None = config("LICENSE", default=None)
    CONTACT_NAME: str | None = config("CONTACT_NAME", default=None)
    CONTACT_EMAIL: str | None = config("CONTACT_EMAIL", default=None)
    SERVICE_URL: str = config("SERVICE_URL", default="http://localhost:8080")
    ENVIRONMENT: EnvironmentOption = config("ENVIRONMENT", default=EnvironmentOption.LOCAL)
    CORS_ORIGINS: list[str] = json.loads(
        config("CORS_ORIGINS", default='["http://localhost:3000", "http://localhost:8080"]')
    )
    RATE_LIMIT_PER_MINUTE: int = config("RATE_LIMIT_PER_MINUTE", default=60)


class DatabaseSettings(BaseSettings):
    """PostgreSQL and Redis connection settings."""

    POSTGRES_URI: str = config(
        "POSTGRES_URI",
        default="postgresql+asyncpg://postgres:password@localhost:5432/work_order_service",
    )
    POSTGRES_SCHEMA: str = config("POSTGRES_SCHEMA", default="fm")
    REDIS_HOST: str = config("REDIS_HOST", default="localhost")
    REDIS_PORT: int = config("REDIS_PORT", default=6379)
    REDIS_USERNAME: str | None = config("REDIS_USERNAME", default="default")
    REDIS_PASSWORD: str | None = config("REDIS_PASSWORD", default=None)
    REDIS_DB: int = config("REDIS_DB", default=0)
    REDIS_RATE_LIMIT_DB: int = config("REDIS_RATE_LIMIT_DB", default=1)
    REDIS_URL: str | None = config("REDIS_URL", default=None)
    REDIS_MAX_CONNECTIONS: int = config("REDIS_MAX_CONNECTIONS", default=20)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = config("REDIS_SOCKET_CONNECT_TIMEOUT", default=5)
    REDIS_SOCKET_TIMEOUT: int = config("REDIS_SOCKET_TIMEOUT", default=5)
    REDIS_RETRY_ON_TIMEOUT: bool = config("REDIS_RETRY_ON_TIMEOUT", default=True)
    REDIS_MAX_RETRIES: int = config("REDIS_MAX_RETRIES", default=3)
    REDIS_RETRY_DELAY: int = config("REDIS_RETRY_DELAY", default=1)

    @property
    def redis_url(self) -> str:
        """Build the Redis connection URL from individual settings or REDIS_URL."""
        if self.REDIS_URL:
            return self.REDIS_URL
        auth_part = f"{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class WorkOrderSettings(BaseSettings):
    """Work-order service feature flags and external integration settings."""

    WOM_SCHEDULER_ENABLED: bool = config("WOM_SCHEDULER_ENABLED", default=True)
    WOM_SCHEDULER_INTERVAL_MINUTES: int = config("WOM_SCHEDULER_INTERVAL_MINUTES", default=60)
    WOM_EMBEDDED_SCHEDULER: bool = config("WOM_EMBEDDED_SCHEDULER", default=True)
    WOM_EMBEDDED_WEBHOOK_WORKER: bool = config("WOM_EMBEDDED_WEBHOOK_WORKER", default=True)
    WOM_WEBHOOK_WORKER_INTERVAL_SECONDS: int = config(
        "WOM_WEBHOOK_WORKER_INTERVAL_SECONDS",
        default=5,
    )
    WOM_WEBHOOK_WORKER_BATCH_SIZE: int = config("WOM_WEBHOOK_WORKER_BATCH_SIZE", default=50)
    WOM_INTERNAL_SERVICE_TOKEN: str | None = config("WOM_INTERNAL_SERVICE_TOKEN", default=None)
    USER_SERVICE_BASE_URL: str = config("USER_SERVICE_BASE_URL", default="http://localhost:5000")
    R2_ACCOUNT_ID: str | None = config("R2_ACCOUNT_ID", default=None)
    R2_ACCESS_KEY: str | None = config("R2_ACCESS_KEY", default=None)
    R2_SECRET_KEY: str | None = config("R2_SECRET_KEY", default=None)
    R2_BUCKET_NAME: str | None = config("R2_BUCKET_NAME", default=None)
    R2_MEDIA_URL: str | None = config("R2_MEDIA_URL", default=None)
    HOA_LICENSE_KEY: str | None = config("HOA_LICENSE_KEY", default=None)
    HOA_APP_SECRET: str | None = config("HOA_APP_SECRET", default=None)
    HOA_BASE_URL: str | None = config("HOA_BASE_URL", default=None)


class Settings(AppSettings, DatabaseSettings, WorkOrderSettings):
    """Combined application settings from all configuration groups."""


settings = Settings()
