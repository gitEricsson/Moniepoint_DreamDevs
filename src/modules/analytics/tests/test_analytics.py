from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.conftest import make_activity

@pytest.fixture
async def seeded_client(db_session: AsyncSession, client: AsyncClient):
    rows = [
        make_activity(merchant_id="MRC-A01", product="POS", amount="900000.00",
                      status="SUCCESS", event_timestamp=datetime(2024, 1, 10, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-A02", product="POS", amount="400000.00",
                      status="SUCCESS", event_timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-A01", product="AIRTIME", amount="5000.00",
                      status="SUCCESS", event_timestamp=datetime(2024, 2, 3, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-A03", product="BILLS", amount="200.00",
                      status="FAILED", event_timestamp=datetime(2024, 1, 20, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-A03", product="BILLS", amount="200.00",
                      status="SUCCESS", event_timestamp=datetime(2024, 1, 21, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-A04", product="KYC",
                      event_type="DOCUMENT_SUBMITTED", amount="0.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-A04", product="KYC",
                      event_type="VERIFICATION_COMPLETED", amount="0.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 3, 5, tzinfo=timezone.utc)),
        make_activity(merchant_id="MRC-A04", product="KYC",
                      event_type="TIER_UPGRADE", amount="0.00", status="SUCCESS",
                      event_timestamp=datetime(2024, 3, 10, tzinfo=timezone.utc)),
    ]
    db_session.add_all(rows)
    await db_session.flush()
    return client

class TestTopMerchant:
    async def test_returns_200(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/top-merchant")
        assert res.status_code == 200

    async def test_response_shape(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/top-merchant")
        data = res.json()
        assert "merchant_id" in data
        assert "total_volume" in data

    async def test_correct_merchant(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/top-merchant")
        data = res.json()
        assert data["merchant_id"] == "MRC-A01"
        assert float(data["total_volume"]) == pytest.approx(905000.0)

class TestMonthlyActiveMerchants:
    async def test_returns_200(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/monthly-active-merchants")
        assert res.status_code == 200

    async def test_response_is_dict(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/monthly-active-merchants")
        data = res.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    async def test_month_key_format(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/monthly-active-merchants")
        keys = list(res.json().keys())
        for key in keys:
            assert len(key) == 7, f"Key {key!r} is not YYYY-MM format"
            year, month = key.split("-")
            assert year.isdigit() and month.isdigit()

    async def test_january_count(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/monthly-active-merchants")
        data = res.json()
        assert data.get("2024-01") == 3

class TestProductAdoption:
    async def test_returns_200(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/product-adoption")
        assert res.status_code == 200

    async def test_response_is_sorted_descending(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/product-adoption")
        counts = list(res.json().values())
        assert counts == sorted(counts, reverse=True)

    async def test_known_products_present(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/product-adoption")
        data = res.json()
        assert "POS" in data
        assert "BILLS" in data
        assert "KYC" in data

class TestKYCFunnel:
    async def test_returns_200(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/kyc-funnel")
        assert res.status_code == 200

    async def test_response_has_three_fields(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/kyc-funnel")
        data = res.json()
        assert "documents_submitted" in data
        assert "verifications_completed" in data
        assert "tier_upgrades" in data

    async def test_funnel_values(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/kyc-funnel")
        data = res.json()
        assert data["documents_submitted"] == 1
        assert data["verifications_completed"] == 1
        assert data["tier_upgrades"] == 1

class TestFailureRates:
    async def test_returns_200(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/failure-rates")
        assert res.status_code == 200

    async def test_response_is_list(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/failure-rates")
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_each_item_has_required_fields(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/failure-rates")
        for item in res.json():
            assert "product" in item
            assert "failure_rate" in item

    async def test_sorted_descending(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/failure-rates")
        rates = [item["failure_rate"] for item in res.json()]
        assert rates == sorted(rates, reverse=True)

    async def test_bills_failure_rate(self, seeded_client: AsyncClient):
        res = await seeded_client.get("/analytics/failure-rates")
        bills = next(
            (item for item in res.json() if item["product"] == "BILLS"), None
        )
        assert bills is not None
        assert bills["failure_rate"] == pytest.approx(50.0, abs=0.1)

class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient):
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
