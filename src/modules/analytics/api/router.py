"""
modules/analytics/api/router.py
──────────────────────────────────────────────────────────────────────────────
FastAPI router definitions mapped to the thin controller layer.
"""
from typing import Annotated
from fastapi import APIRouter, Depends

from src.modules.analytics.schemas.analytics import (
    FailureRateItem,
    KYCFunnelResponse,
    TopMerchantResponse,
    MONTHLY_ACTIVE_MERCHANTS_RESPONSES,
    PRODUCT_ADOPTION_RESPONSES,
)
from src.modules.analytics.services.analytics_service import AnalyticsService
from src.modules.analytics.controllers.analytics_controller import AnalyticsController

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_Service = Annotated[AnalyticsService, Depends(AnalyticsService)]

@router.get(
    "/top-merchant",
    response_model=TopMerchantResponse,
    summary="Merchant with highest total successful transaction volume",
)
async def top_merchant(service: _Service) -> TopMerchantResponse:
    return await AnalyticsController(service).top_merchant()

@router.get(
    "/monthly-active-merchants",
    response_model=dict[str, int],
    summary="Unique active merchant count per calendar month",
    responses=MONTHLY_ACTIVE_MERCHANTS_RESPONSES,
)
async def monthly_active_merchants(service: _Service) -> dict[str, int]:
    return await AnalyticsController(service).monthly_active_merchants()

@router.get(
    "/product-adoption",
    response_model=dict[str, int],
    summary="Unique merchant count per product, sorted ascending",
    responses=PRODUCT_ADOPTION_RESPONSES,
)
async def product_adoption(service: _Service) -> dict[str, int]:
    return await AnalyticsController(service).product_adoption()

@router.get(
    "/kyc-funnel",
    response_model=KYCFunnelResponse,
    summary="KYC conversion funnel: documents → verification → tier upgrade",
)
async def kyc_funnel(service: _Service) -> KYCFunnelResponse:
    return await AnalyticsController(service).kyc_funnel()

@router.get(
    "/failure-rates",
    response_model=list[FailureRateItem],
    summary="Transaction failure rate per product, sorted descending",
)
async def failure_rates(service: _Service) -> list[FailureRateItem]:
    return await AnalyticsController(service).failure_rates()
