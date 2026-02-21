from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

VALID_PRODUCTS = frozenset(
    {"POS", "AIRTIME", "BILLS", "CARD_PAYMENT", "SAVINGS", "MONIEBOOK", "KYC"}
)
VALID_STATUSES = frozenset({"SUCCESS", "FAILED", "PENDING"})
VALID_CHANNELS = frozenset({"POS", "APP", "USSD", "WEB", "OFFLINE"})

class ActivityCreate(BaseModel):

    event_id: uuid.UUID
    merchant_id: str
    event_timestamp: datetime
    product: str
    event_type: str
    amount: Decimal
    status: str
    channel: str | None = None
    region: str | None = None
    merchant_tier: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v: object) -> Decimal:
        try:
            return Decimal(str(v))
        except Exception:
            return Decimal("0.00")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: object) -> str:
        val = str(v).strip().upper()
        if val not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {v!r}")
        return val

    @field_validator("product", mode="before")
    @classmethod
    def validate_product(cls, v: object) -> str:
        val = str(v).strip().upper()
        if val not in VALID_PRODUCTS:
            raise ValueError(f"Invalid product: {v!r}")
        return val

    @field_validator("channel", mode="before")
    @classmethod
    def validate_channel(cls, v: object) -> str | None:
        if not v or str(v).strip() == "":
            return None
        val = str(v).strip().upper()
        return val if val in VALID_CHANNELS else None

    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values: dict) -> dict:
        merchant_id = str(values.get("merchant_id", "")).strip()
        timestamp = str(values.get("event_timestamp", "")).strip()

        if not merchant_id:
            raise ValueError("merchant_id is required")
        if not timestamp:
            raise ValueError("event_timestamp is required")
        return values

    def to_db_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "merchant_id": self.merchant_id,
            "event_timestamp": self.event_timestamp,
            "product": self.product,
            "event_type": self.event_type,
            "amount": self.amount,
            "status": self.status,
            "channel": self.channel,
            "region": self.region,
            "merchant_tier": self.merchant_tier,
        }
