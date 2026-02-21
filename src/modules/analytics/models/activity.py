"""
models/activity.py
──────────────────────────────────────────────────────────────────────────────
ORM model for the merchant_activities table.

Index strategy (DSA highlights):
  ┌─────────────────────────────────────┬───────────────────────────────────┐
  │ Index                               │ Queries it accelerates            │
  ├─────────────────────────────────────┼───────────────────────────────────┤
  │ ix_ma_merchant_id                   │ top-merchant (GROUP BY/SUM)       │
  │ ix_ma_status_product (composite)    │ failure-rates, product-adoption   │
  │ ix_ma_status (partial filter)       │ monthly-active, top-merchant      │
  │ ix_ma_product_kyc (partial, KYC)    │ kyc-funnel (very selective)       │
  │ Primary key on event_id (UUID)      │ duplicate detection on insert     │
  └─────────────────────────────────────┴───────────────────────────────────┘
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class MerchantActivity(Base):
    __tablename__ = "merchant_activities"

    # ── Columns ───────────────────────────────────────────────────────────────
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[str] = mapped_column(String(20), nullable=False)
    event_timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    product: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Numeric] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(15), nullable=True)
    region: Mapped[str | None] = mapped_column(String(30), nullable=True)
    merchant_tier: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # ── Indexes ───────────────────────────────────────────────────────────────
    __table_args__ = (
        # Composite covering index: status + product eliminates full-table
        # scans for failure-rate and product-adoption queries.
        Index("ix_ma_status_product", "status", "product"),

        # Merchant-level index: accelerates GROUP BY merchant_id + SUM(amount).
        Index("ix_ma_merchant_id", "merchant_id"),

        # Timestamp index: used for monthly bucketing (date_trunc / to_char).
        Index("ix_ma_event_timestamp", "event_timestamp"),

        # Partial index — only KYC rows: very high selectivity for kyc-funnel.
        Index(
            "ix_ma_kyc_partial",
            "product",
            "event_type",
            "merchant_id",
            postgresql_where="product = 'KYC' AND status = 'SUCCESS'",
        ),

        # DB-level uniqueness guard (mirrors primary key but explicit).
        UniqueConstraint("event_id", name="uq_ma_event_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<MerchantActivity event_id={self.event_id} "
            f"merchant={self.merchant_id} product={self.product} "
            f"status={self.status}>"
        )
