"""
repositories/activity_repository.py
──────────────────────────────────────────────────────────────────────────────
Data-access layer for writing activity records.

DSA/Performance notes:
  • Uses PostgreSQL's INSERT … ON CONFLICT DO NOTHING (upsert) so duplicate
    event_ids from the CSV (or re-import runs) are silently skipped at the DB
    level — O(1) per row via primary-key B-tree lookup.
  • Bulk execution: SQLAlchemy passes the list as a prepared-statement
    executemany which asyncpg serialises into a pipelined protocol batch —
    far cheaper than N round-trips.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.analytics.models.activity import MerchantActivity


class ActivityRepository:
    """Encapsulates all write operations on merchant_activities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Write ─────────────────────────────────────────────────────────────────

    async def bulk_insert(self, records: list[dict]) -> int:
        """
        Insert a batch of activity dicts, skipping duplicates.

        Uses PostgreSQL INSERT … ON CONFLICT DO NOTHING so:
          • Re-running the importer is safe (idempotent).
          • Duplicates within a CSV batch are silently discarded.

        Returns the number of records passed in (not necessarily all inserted).
        """
        if not records:
            return 0

        stmt = pg_insert(MerchantActivity).on_conflict_do_nothing(
            index_elements=["event_id"]
        )
        await self.db.execute(stmt, records)
        await self.db.commit()
        return len(records)

    # ── Read ──────────────────────────────────────────────────────────────────

    async def count_total(self) -> int:
        """Return the total number of rows currently in the table."""
        stmt = select(func.count()).select_from(MerchantActivity)
        result = await self.db.execute(stmt)
        return result.scalar_one()
