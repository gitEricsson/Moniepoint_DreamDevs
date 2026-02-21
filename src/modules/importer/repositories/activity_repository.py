from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.models.activity import MerchantActivity

class ActivityRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def bulk_insert(self, records: list[dict]) -> int:
        if not records:
            return 0

        stmt = pg_insert(MerchantActivity).on_conflict_do_nothing(
            index_elements=["event_id"]
        )
        await self.db.execute(stmt, records)
        await self.db.commit()
        return len(records)

    async def count_total(self) -> int:
        stmt = select(func.count()).select_from(MerchantActivity)
        result = await self.db.execute(stmt)
        return result.scalar_one()
