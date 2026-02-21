"""
repositories/analytics_repository.py
──────────────────────────────────────────────────────────────────────────────
Read-only analytics queries using SQLAlchemy Core select() + func.*.

All queries use a single GROUP BY aggregation pushed down to PostgreSQL —
no Python-level aggregation, which would be O(N) in application memory.

DSA highlights per query:
  Q1 top-merchant    : O(N) hash-aggregate → sort → LIMIT 1
  Q2 monthly-active  : O(N) hash-aggregate on month bucket, COUNT(DISTINCT)
  Q3 product-adoption: O(N) hash-aggregate per product, COUNT(DISTINCT)
  Q4 kyc-funnel      : uses partial index ix_ma_kyc_partial → near O(log N)
  Q5 failure-rates   : O(N) conditional SUM (CASE WHEN) per product group
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement

from src.modules.analytics.models.activity import MerchantActivity


class month_bucket(FunctionElement):
    """Custom SQL function to truncate a timestamp to YYYY-MM across dialects."""
    type = String()
    name = 'month_bucket'
    inherit_cache = True

@compiles(month_bucket, 'postgresql')
def compile_month_bucket_pg(element, compiler, **kw):
    return f"to_char({compiler.process(element.clauses, **kw)}, 'YYYY-MM')"

@compiles(month_bucket, 'sqlite')
def compile_month_bucket_sqlite(element, compiler, **kw):
    return f"strftime('%Y-%m', {compiler.process(element.clauses, **kw)})"


class AnalyticsRepository:
    """All read-heavy analytics queries against merchant_activities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Q1: Top Merchant ──────────────────────────────────────────────────────

    async def get_top_merchant(self) -> tuple[str, Decimal] | None:
        """
        Returns (merchant_id, total_volume) for the merchant with the highest
        cumulative successful transaction amount across ALL products.
        """
        total_volume = func.sum(MerchantActivity.amount).label("total_volume")

        stmt = (
            select(
                MerchantActivity.merchant_id,
                total_volume,
            )
            .where(MerchantActivity.status == "SUCCESS")
            .group_by(MerchantActivity.merchant_id)
            .order_by(total_volume.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        return row.merchant_id, Decimal(str(row.total_volume))

    # ── Q2: Monthly Active Merchants ──────────────────────────────────────────

    async def get_monthly_active_merchants(self) -> dict[str, int]:
        """
        Returns {YYYY-MM: unique_merchant_count} for months with at least one
        successful event.

        DSA note: PostgreSQL hash-aggregate on to_char(timestamp, 'YYYY-MM') —
        the result set is at most 12 rows (one per month), so sorting is O(1).
        """
        month_col = month_bucket(MerchantActivity.event_timestamp).label("month")

        unique_merchants = func.count(
            func.distinct(MerchantActivity.merchant_id)
        ).label("active_merchants")

        stmt = (
            select(month_col, unique_merchants)
            .where(MerchantActivity.status == "SUCCESS")
            .group_by(month_col)
            .order_by(month_col)
        )

        result = await self.db.execute(stmt)
        return {row.month: row.active_merchants for row in result.all()}

    # ── Q3: Product Adoption ──────────────────────────────────────────────────

    async def get_product_adoption(self) -> dict[str, int]:
        """
        Returns {product: unique_merchant_count}, sorted by count descending.

        No status filter — adoption = any interaction with the product.
        """
        merchant_count = func.count(
            func.distinct(MerchantActivity.merchant_id)
        ).label("merchant_count")

        stmt = (
            select(MerchantActivity.product, merchant_count)
            .group_by(MerchantActivity.product)
            .order_by(merchant_count.desc())
        )

        result = await self.db.execute(stmt)
        return {row.product: row.merchant_count for row in result.all()}

    # ── Q4: KYC Funnel ────────────────────────────────────────────────────────

    async def get_kyc_funnel(self) -> dict[str, int]:
        """
        Returns unique merchant counts at each KYC stage (SUCCESS only).

        Uses the partial index ix_ma_kyc_partial for O(log N) access instead
        of scanning the full table.

        Returns raw {event_type: count} mapping; the service layer reshapes it
        into the named response fields.
        """
        merchant_count = func.count(
            func.distinct(MerchantActivity.merchant_id)
        ).label("merchant_count")

        stmt = (
            select(MerchantActivity.event_type, merchant_count)
            .where(
                MerchantActivity.product == "KYC",
                MerchantActivity.status == "SUCCESS",
            )
            .group_by(MerchantActivity.event_type)
        )

        result = await self.db.execute(stmt)
        return {row.event_type: row.merchant_count for row in result.all()}

    # ── Q5: Failure Rates ─────────────────────────────────────────────────────

    async def get_failure_rates(self) -> list[dict]:
        """
        Returns [{product, failure_rate}] sorted by rate descending.

        Formula: FAILED / (SUCCESS + FAILED) * 100, PENDING excluded.

        DSA note: conditional SUM (CASE WHEN) avoids a self-join or subquery —
        single-pass O(N) aggregation.
        """
        failed_sum = func.sum(
            case((MerchantActivity.status == "FAILED", 1), else_=0)
        )
        total_sum = func.sum(
            case(
                (MerchantActivity.status.in_(["SUCCESS", "FAILED"]), 1),
                else_=0,
            )
        )

        # Cast to Numeric for precise division; NULLIF guards division-by-zero
        failure_rate = func.round(
            cast(failed_sum, Numeric(18, 4))
            * 100
            / func.nullif(cast(total_sum, Numeric(18, 4)), 0),
            1,
        ).label("failure_rate")

        stmt = (
            select(
                MerchantActivity.product,
                failure_rate,
            )
            .where(MerchantActivity.status.in_(["SUCCESS", "FAILED"]))
            .group_by(MerchantActivity.product)
            .order_by(failure_rate.desc())
        )

        result = await self.db.execute(stmt)
        return [
            {
                "product": row.product,
                "failure_rate": Decimal(str(row.failure_rate or 0)),
            }
            for row in result.all()
        ]
