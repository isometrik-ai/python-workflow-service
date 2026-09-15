"""API routes for maintenance contracts."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.contract_service import ContractService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse
from app.schemas.common import ApiKeyScope
from app.schemas.contracts import (
    ContractDetailDataResponse,
    ContractListDataResponse,
    ContractResponse,
    CreateContractRequest,
    UpdateContractRequest,
)

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": ContractListDataResponse,
            "description": "Contracts retrieved successfully",
        },
        **common_responses,
    },
    summary="List maintenance contracts",
)
async def list_contracts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated maintenance contracts for the authenticated tenant/project."""
    service = ContractService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list(page=page, page_size=page_size, status=status)
    payload = [ContractResponse.model_validate(item).model_dump(mode="json") for item in items]
    return list_response(
        request=request,
        items=payload,
        total=total,
        page=page,
        page_size=page_size,
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
    )


@router.get(
    "/{contract_id}",
    response_model=None,
    responses={
        200: {
            "model": ContractDetailDataResponse,
            "description": "Contract retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Contract not found"},
        **common_responses,
    },
    summary="Get maintenance contract",
)
async def get_contract(
    request: Request,
    contract_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single maintenance contract by ID."""
    service = ContractService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(contract_id)
    payload = ContractResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    responses={
        201: {
            "model": ContractDetailDataResponse,
            "description": "Contract created successfully",
        },
        **common_responses,
    },
    summary="Create maintenance contract",
)
async def create_contract(
    request: Request,
    body: CreateContractRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new maintenance contract."""
    service = ContractService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(body.model_dump(mode="json"))
    payload = ContractResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{contract_id}",
    response_model=None,
    responses={
        200: {
            "model": ContractDetailDataResponse,
            "description": "Contract updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Contract not found"},
        **common_responses,
    },
    summary="Update maintenance contract",
)
async def update_contract(
    request: Request,
    contract_id: str,
    body: UpdateContractRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing maintenance contract."""
    service = ContractService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(contract_id, body.model_dump(exclude_unset=True, mode="json"))
    payload = ContractResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{contract_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Contract deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Contract not found"},
        **common_responses,
    },
    summary="Delete maintenance contract",
)
async def delete_contract(
    request: Request,
    contract_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a maintenance contract."""
    service = ContractService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(contract_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
