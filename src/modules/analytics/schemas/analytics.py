"""
schemas/analytics.py
──────────────────────────────────────────────────────────────────────────────
Pydantic v2 response schemas for all 5 analytics endpoints.

Decimal precision rules (from spec):
  • Monetary values  → 2 decimal places
  • Percentages      → 1 decimal place
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, field_serializer


class TopMerchantResponse(BaseModel):
    """GET /analytics/top-merchant"""

    merchant_id: str
    total_volume: Decimal

    @field_serializer("total_volume")
    def format_volume(self, v: Decimal) -> float:
        return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_id": "MRC-001234",
                "total_volume": 98765432.10
            }
        }
    }


class FailureRateItem(BaseModel):
    """One entry in GET /analytics/failure-rates"""

    product: str
    failure_rate: Decimal

    @field_serializer("failure_rate")
    def format_rate(self, v: Decimal) -> float:
        return float(v.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

    model_config = {
        "json_schema_extra": {
            "example": {
                "product": "BILLS",
                "failure_rate": 5.2
            }
        }
    }


class KYCFunnelResponse(BaseModel):
    """GET /analytics/kyc-funnel"""

    documents_submitted: int
    verifications_completed: int
    tier_upgrades: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "documents_submitted": 5432,
                "verifications_completed": 4521,
                "tier_upgrades": 3890
            }
        }
    }


class ImportSummary(BaseModel):
    """Internal – returned by the import service for logging/health checks."""

    files_processed: int
    rows_inserted: int
    rows_skipped: int
    already_loaded: bool = False


MONTHLY_ACTIVE_MERCHANTS_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {"2024-01": 8234, "2024-02": 8456}
            }
        }
    }
}


PRODUCT_ADOPTION_RESPONSES = {
    200: {
        "content": {
            "application/json": {
                "example": {"POS": 15234, "AIRTIME": 12456, "BILLS": 10234}
            }
        }
    }
}
