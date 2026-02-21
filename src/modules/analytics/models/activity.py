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

    __table_args__ = (
        Index("ix_ma_status_product", "status", "product"),

        Index("ix_ma_merchant_id", "merchant_id"),

        Index("ix_ma_event_timestamp", "event_timestamp"),

        Index(
            "ix_ma_kyc_partial",
            "product",
            "event_type",
            "merchant_id",
            postgresql_where="product = 'KYC' AND status = 'SUCCESS'",
        ),

        UniqueConstraint("event_id", name="uq_ma_event_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<MerchantActivity event_id={self.event_id} "
            f"merchant={self.merchant_id} product={self.product} "
            f"status={self.status}>"
        )
