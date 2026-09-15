"""Top-level API router aggregating versioned endpoints."""

from fastapi import APIRouter

from app.api.mcp import router as mcp_router
from app.api.v1 import router as v1_router

router = APIRouter(prefix="/api")
router.include_router(v1_router)
router.include_router(mcp_router)
