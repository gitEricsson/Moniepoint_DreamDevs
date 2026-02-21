from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.importer.repositories.activity_repository import ActivityRepository
from src.modules.analytics.repositories.analytics_repository import AnalyticsRepository
from src.conftest import make_activity

class TestActivityRepository:

    async def test_count_total_empty(self, db_session: AsyncSession):
        repo = ActivityRepository(db_session)
        count = await repo.count_total()
        assert count == 0

    async def test_bulk_insert_returns_count(self, db_session: AsyncSession):
        repo = ActivityRepository(db_session)
        rows = [make_activity(merchant_id=f"MRC-00000{i}") for i in range(5)]
        dicts = [
            {
                "event_id": r.event_id,
                "merchant_id": r.merchant_id,
                "event_timestamp": r.event_timestamp,
                "product": r.product,
                "event_type": r.event_type,
                "amount": r.amount,
                "status": r.status,
                "channel": r.channel,
                "region": r.region,
                "merchant_tier": r.merchant_tier,
            }
            for r in rows
        ]
        result = await repo.bulk_insert(dicts)
        assert result == 5

@pytest_asyncio.fixture
async def seeded_session(db_session: AsyncSession) -> AsyncSession:
    rows = [
        make_activity(merchant_id="MRC-000001", product="POS", amount="500000.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000001", product="AIRTIME", amount="100000.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 2, 5, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000002", product="POS", amount="300000.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 1, 20, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000003", product="BILLS", amount="50000.00", status="FAILED",
                      event_timestamp=datetime(2024, 1, 25, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000003", product="BILLS", amount="10000.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 1, 26, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000004", product="KYC", event_type="DOCUMENT_SUBMITTED",
                      amount="0.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000005", product="KYC", event_type="DOCUMENT_SUBMITTED",
                      amount="0.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 3, 2, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000004", product="KYC", event_type="VERIFICATION_COMPLETED",
                      amount="0.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 3, 5, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-000004", product="KYC", event_type="TIER_UPGRADE",
                      amount="0.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 3, 10, tzinfo=timezone.utc)),
    ]
    db_session.add_all(rows)
    await db_session.flush()
    return db_session

class TestAnalyticsRepository:

    async def test_top_merchant_returns_highest_volume(
        self, seeded_session: AsyncSession
    ):
        repo = AnalyticsRepository(seeded_session)
        result = await repo.get_top_merchant()
        assert result is not None
        merchant_id, volume = result
        assert merchant_id == "MRC-000001"
        assert volume == Decimal("600000.00")

    async def test_monthly_active_merchants_counts(
        self, seeded_session: AsyncSession
    ):
        repo = AnalyticsRepository(seeded_session)
        monthly = await repo.get_monthly_active_merchants()
        assert "2024-01" in monthly
        assert monthly["2024-01"] == 3
        assert monthly["2024-02"] == 1
        assert monthly["2024-03"] == 2

    async def test_product_adoption_sorted_desc(
        self, seeded_session: AsyncSession
    ):
        repo = AnalyticsRepository(seeded_session)
        adoption = await repo.get_product_adoption()
        products = list(adoption.keys())
        counts = list(adoption.values())
        assert counts == sorted(counts, reverse=True)
        assert adoption.get("POS", 0) >= 2

    async def test_kyc_funnel_values(self, seeded_session: AsyncSession):
        repo = AnalyticsRepository(seeded_session)
        funnel = await repo.get_kyc_funnel()
        assert funnel.get("DOCUMENT_SUBMITTED") == 2
        assert funnel.get("VERIFICATION_COMPLETED") == 1
        assert funnel.get("TIER_UPGRADE") == 1

    async def test_failure_rates_formula(self, seeded_session: AsyncSession):
        repo = AnalyticsRepository(seeded_session)
        rates = await repo.get_failure_rates()
        bills = next((r for r in rates if r["product"] == "BILLS"), None)
        assert bills is not None
        assert bills["failure_rate"] == Decimal("50.0")

    async def test_failure_rates_sorted_desc(self, seeded_session: AsyncSession):
        repo = AnalyticsRepository(seeded_session)
        rates = await repo.get_failure_rates()
        values = [r["failure_rate"] for r in rates]
        assert values == sorted(values, reverse=True)
