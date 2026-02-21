from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement

from src.modules.analytics.models.activity import MerchantActivity

class month_bucket(FunctionElement):
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

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_top_merchant(self) -> tuple[str, Decimal] | None:
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

    async def get_monthly_active_merchants(self) -> dict[str, int]:
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

    async def get_product_adoption(self) -> dict[str, int]:
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

    async def get_kyc_funnel(self) -> dict[str, int]:
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

    async def get_failure_rates(self) -> list[dict]:
        failed_sum = func.sum(
            case((MerchantActivity.status == "FAILED", 1), else_=0)
        )
        total_sum = func.sum(
            case(
                (MerchantActivity.status.in_(["SUCCESS", "FAILED"]), 1),
                else_=0,
            )
        )

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
