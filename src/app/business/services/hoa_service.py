"""House of Apps CRM service wrapper with httpx fallback."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi.concurrency import run_in_threadpool

from app.core.config.app_config import settings

logger = logging.getLogger("hoa")

_client: Any = None
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 300
HOA_TIMEOUT = 4


def _format_company(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a HoA company record to the vendor response shape."""
    return {
        "id": str(item.get("id", "")),
        "name": str(item.get("name", "")),
        "email": str(item.get("email", "")),
        "phone": str(item.get("phone", "")),
        "industry": str(item.get("industry", "")),
        "status": str(item.get("status", "")),
        "source": "houseofapps",
    }


def _get_client() -> Any:
    """Return a cached HouseOfApps SDK client when credentials are configured."""
    global _client
    if _client is None:
        from houseofapps import HouseOfApps  # pylint: disable=import-error

        _client = HouseOfApps(
            license_key=settings.HOA_LICENSE_KEY,
            app_secret=settings.HOA_APP_SECRET,
            base_url=settings.HOA_BASE_URL,
            timeout=HOA_TIMEOUT,
        )
    return _client


def _sdk_configured() -> bool:
    """Return True when HoA SDK credentials are present."""
    return bool(settings.HOA_LICENSE_KEY and settings.HOA_APP_SECRET and settings.HOA_BASE_URL)


def _search_companies_sync(query: str, page: int = 1, page_size: int = 50) -> list[dict[str, Any]]:
    """Search companies via the HouseOfApps SDK (sync)."""
    client = _get_client()
    result = client.companies.list(search=query, page=page, page_size=page_size)
    return [_format_company(item) for item in result.items]


def _list_companies_sync(page: int = 1, page_size: int = 100) -> list[dict[str, Any]]:
    """List companies via the HouseOfApps SDK (sync)."""
    client = _get_client()
    result = client.companies.list(page=page, page_size=page_size)
    return [_format_company(item) for item in result.items]


def _create_company_sync(name: str, **kwargs: Any) -> dict[str, Any]:
    """Create a company via the HouseOfApps SDK (sync)."""
    client = _get_client()
    result = client.companies.create({"name": name, **kwargs})
    return _format_company(result)


async def _httpx_list_companies(page: int = 1, page_size: int = 100) -> list[dict[str, Any]]:
    """List companies via HoA REST API using httpx."""
    import httpx

    url = f"{settings.HOA_BASE_URL.rstrip('/')}/companies"
    headers = {
        "X-License-Key": settings.HOA_LICENSE_KEY,
        "X-App-Secret": settings.HOA_APP_SECRET,
    }
    async with httpx.AsyncClient(timeout=HOA_TIMEOUT) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"page": page, "page_size": page_size},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") or payload.get("data") or payload
        if isinstance(items, dict):
            items = items.get("items", [])
        return [_format_company(item) for item in items]


async def _httpx_search_companies(
    query: str,
    page: int = 1,
    page_size: int = 50,
) -> list[dict[str, Any]]:
    """Search companies via HoA REST API using httpx."""
    import httpx

    url = f"{settings.HOA_BASE_URL.rstrip('/')}/companies"
    headers = {
        "X-License-Key": settings.HOA_LICENSE_KEY,
        "X-App-Secret": settings.HOA_APP_SECRET,
    }
    async with httpx.AsyncClient(timeout=HOA_TIMEOUT) as client:
        response = await client.get(
            url,
            headers=headers,
            params={"search": query, "page": page, "page_size": page_size},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") or payload.get("data") or payload
        if isinstance(items, dict):
            items = items.get("items", [])
        return [_format_company(item) for item in items]


async def _httpx_create_company(name: str, **kwargs: Any) -> dict[str, Any]:
    """Create a company via HoA REST API using httpx."""
    import httpx

    url = f"{settings.HOA_BASE_URL.rstrip('/')}/companies"
    headers = {
        "X-License-Key": settings.HOA_LICENSE_KEY,
        "X-App-Secret": settings.HOA_APP_SECRET,
    }
    async with httpx.AsyncClient(timeout=HOA_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json={"name": name, **kwargs})
        response.raise_for_status()
        return _format_company(response.json())


async def _run_sync(fn: Any, *args: Any, timeout: float = HOA_TIMEOUT + 2) -> Any:
    """Run a sync function in a thread pool with a timeout."""
    return await asyncio.wait_for(run_in_threadpool(fn, *args), timeout=timeout)


async def _try_list(page: int, page_size: int) -> list[dict[str, Any]]:
    """Attempt HoA list via SDK or httpx."""
    if not _sdk_configured():
        raise RuntimeError("HoA not configured")
    try:
        return await _run_sync(_list_companies_sync, page, page_size)
    except ImportError:
        return await _httpx_list_companies(page, page_size)


async def _try_search(query: str, page: int, page_size: int) -> list[dict[str, Any]]:
    """Attempt HoA search via SDK or httpx."""
    if not _sdk_configured():
        raise RuntimeError("HoA not configured")
    try:
        return await _run_sync(_search_companies_sync, query, page, page_size)
    except ImportError:
        return await _httpx_search_companies(query, page, page_size)


async def _try_create(name: str, **kwargs: Any) -> dict[str, Any]:
    """Attempt HoA create via SDK or httpx."""
    if not _sdk_configured():
        raise RuntimeError("HoA not configured")
    try:
        return await _run_sync(_create_company_sync, name, **kwargs)
    except ImportError:
        return await _httpx_create_company(name, **kwargs)


async def search_companies(
    query: str,
    page: int = 1,
    page_size: int = 50,
    fallback: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Search HoA companies with cache and local fallback."""
    cache_key = f"search:{query}:{page}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]
    try:
        result = await _try_search(query, page, page_size)
        _cache[cache_key] = (time.time(), result)
        return result
    except Exception as exc:
        logger.warning("HoA search failed (%s: %s) — using fallback", type(exc).__name__, exc)
        if fallback:
            ql = query.lower()
            return [vendor for vendor in fallback if ql in vendor.get("name", "").lower()]
        return []


async def list_companies(
    page: int = 1,
    page_size: int = 100,
    fallback: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """List HoA companies with cache and local fallback."""
    cache_key = f"list:{page}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]
    try:
        result = await _try_list(page, page_size)
        _cache[cache_key] = (time.time(), result)
        return result
    except Exception as exc:
        logger.warning("HoA list failed (%s: %s) — using fallback", type(exc).__name__, exc)
        return fallback or []


async def create_company(name: str, **kwargs: Any) -> dict[str, Any]:
    """Create a HoA company, falling back to a local vendor id on failure."""
    _cache.clear()
    try:
        return await _try_create(name, **kwargs)
    except Exception as exc:
        logger.warning("HoA create failed (%s: %s) — using local vendor", type(exc).__name__, exc)
        return {
            "id": f"ven-local-{abs(hash(name)) % 100000}",
            "name": name,
            "email": "",
            "phone": "",
            "industry": "",
            "status": "",
            "source": "local",
        }
