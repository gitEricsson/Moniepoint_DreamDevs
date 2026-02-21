"""
services/analytics_service.py
──────────────────────────────────────────────────────────────────────────────
Business logic + response shaping for all 5 analytics endpoints.

This layer sits between the controller (HTTP) and the repository (data access).
It is responsible for:
  • Calling the repository
  • Mapping raw DB rows to typed Pydantic response schemas
  • Raising FastAPI HTTPExceptions when no data is available
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.modules.analytics.repositories.analytics_repository import AnalyticsRepository
from src.modules.analytics.schemas.analytics import (
    FailureRateItem,
    KYCFunnelResponse,
    TopMerchantResponse,
)

# KYC event_type → response field mapping
_KYC_FIELD_MAP: dict[str, str] = {
    "DOCUMENT_SUBMITTED": "documents_submitted",
    "VERIFICATION_COMPLETED": "verifications_completed",
    "TIER_UPGRADE": "tier_upgrades",
}


class AnalyticsService:
    """Orchestrates analytics data retrieval and response formatting."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self._repo = AnalyticsRepository(db)

    # ── Endpoint 1 ────────────────────────────────────────────────────────────

    async def get_top_merchant(self) -> TopMerchantResponse:
        result = await self._repo.get_top_merchant()
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No successful transactions found.",
            )
        merchant_id, total_volume = result
        return TopMerchantResponse(
            merchant_id=merchant_id,
            total_volume=total_volume,
        )

    # ── Endpoint 2 ────────────────────────────────────────────────────────────

    async def get_monthly_active_merchants(self) -> dict[str, int]:
        data = await self._repo.get_monthly_active_merchants()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active merchant data found.",
            )
        return data

    # ── Endpoint 3 ────────────────────────────────────────────────────────────

    async def get_product_adoption(self) -> dict[str, int]:
        data = await self._repo.get_product_adoption()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No product adoption data found.",
            )
        return data

    # ── Endpoint 4 ────────────────────────────────────────────────────────────

    async def get_kyc_funnel(self) -> KYCFunnelResponse:
        raw = await self._repo.get_kyc_funnel()

        # Map event_type values to the three response fields
        funnel: dict[str, int] = {
            "documents_submitted": 0,
            "verifications_completed": 0,
            "tier_upgrades": 0,
        }
        for event_type, count in raw.items():
            field = _KYC_FIELD_MAP.get(event_type.upper())
            if field:
                funnel[field] = count

        return KYCFunnelResponse(**funnel)

    # ── Endpoint 5 ────────────────────────────────────────────────────────────

    async def get_failure_rates(self) -> list[FailureRateItem]:
        rows = await self._repo.get_failure_rates()
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No failure rate data found.",
            )
        return [
            FailureRateItem(
                product=row["product"],
                failure_rate=Decimal(str(row["failure_rate"])),
            )
            for row in rows
        ]
