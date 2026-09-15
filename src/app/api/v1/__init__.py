"""Version 1 API router for work-order domain endpoints."""

from fastapi import APIRouter

from app.api.v1.api_keys import router as api_keys_router
from app.api.v1.asset_categories import router as asset_categories_router
from app.api.v1.assets import router as assets_router
from app.api.v1.business_profile import router as business_profile_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.custom_fields import router as custom_fields_router
from app.api.v1.form_templates import router as form_templates_router
from app.api.v1.health import router as health_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.logs import router as logs_router
from app.api.v1.payments import router as payments_router
from app.api.v1.pdf_templates import router as pdf_templates_router
from app.api.v1.presigned_url import router as presigned_url_router
from app.api.v1.scheduler import router as scheduler_router
from app.api.v1.triggers import router as triggers_router
from app.api.v1.vendor_portal import router as vendor_portal_router
from app.api.v1.vendors import router as vendors_router
from app.api.v1.work_orders import router as work_orders_router

router = APIRouter(prefix="/v1")
router.include_router(health_router)
router.include_router(api_keys_router)
router.include_router(asset_categories_router)
router.include_router(assets_router)
router.include_router(custom_fields_router)
router.include_router(business_profile_router)
router.include_router(pdf_templates_router)
router.include_router(vendors_router)
router.include_router(form_templates_router)
router.include_router(contracts_router)
router.include_router(work_orders_router)
router.include_router(invoices_router)
router.include_router(payments_router)
router.include_router(triggers_router)
router.include_router(logs_router)
router.include_router(scheduler_router)
router.include_router(vendor_portal_router)
router.include_router(presigned_url_router)
