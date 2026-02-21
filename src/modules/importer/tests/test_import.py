"""
tests/test_import.py
──────────────────────────────────────────────────────────────────────────────
Unit tests for the CSV import pipeline.

Tests cover:
  • Valid row → parsed correctly
  • Missing merchant_id → skipped
  • Missing event_timestamp → skipped
  • Invalid amount ('INVALID') → coerced to 0.00
  • Invalid status → skipped
  • Duplicate event_id (in-memory set) → skipped
  • Invalid product → skipped
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from src.modules.importer.schemas.activity import ActivityCreate
from src.modules.importer.services.import_service import CSVImportService


# ── _parse_row unit tests ──────────────────────────────────────────────────────

class TestParseRow:
    """Tests for CSVImportService._parse_row — the per-row validation gate."""

    def _parse(self, raw: dict, seen: set | None = None) -> tuple:
        return CSVImportService._parse_row(raw, seen or set())

    def _valid_row(self, **overrides) -> dict:
        base = {
            "event_id": str(uuid.uuid4()),
            "merchant_id": "MRC-000001",
            "event_timestamp": "2024-01-09T10:00:00",
            "product": "POS",
            "event_type": "CARD_TRANSACTION",
            "amount": "1500.50",
            "status": "SUCCESS",
            "channel": "POS",
            "region": "LAGOS",
            "merchant_tier": "VERIFIED",
        }
        base.update(overrides)
        return base

    def test_valid_row_parses_correctly(self):
        row = self._valid_row()
        record, ok = self._parse(row)
        assert ok is True
        assert record["merchant_id"] == "MRC-000001"
        assert record["amount"] == Decimal("1500.50")
        assert record["status"] == "SUCCESS"

    def test_missing_merchant_id_skipped(self):
        row = self._valid_row(merchant_id="")
        _, ok = self._parse(row)
        assert ok is False

    def test_missing_event_timestamp_skipped(self):
        row = self._valid_row(event_timestamp="")
        _, ok = self._parse(row)
        assert ok is False

    def test_invalid_amount_coerced_to_zero(self):
        """Non-numeric amount should be coerced to 0.00, not skip the row."""
        row = self._valid_row(amount="INVALID")
        record, ok = self._parse(row)
        assert ok is True
        assert record["amount"] == Decimal("0.00")

    def test_invalid_status_skipped(self):
        row = self._valid_row(status="UNKNOWN_STATUS")
        _, ok = self._parse(row)
        assert ok is False

    def test_invalid_product_skipped(self):
        row = self._valid_row(product="CRYPTO")
        _, ok = self._parse(row)
        assert ok is False

    def test_duplicate_event_id_skipped(self):
        row = self._valid_row()
        eid = uuid.UUID(row["event_id"])
        seen: set[uuid.UUID] = {eid}
        _, ok = self._parse(row, seen)
        assert ok is False

    def test_malformed_event_id_skipped(self):
        row = self._valid_row(event_id="not-a-uuid")
        _, ok = self._parse(row)
        assert ok is False

    def test_empty_event_id_skipped(self):
        row = self._valid_row(event_id="")
        _, ok = self._parse(row)
        assert ok is False

    def test_pending_status_accepted(self):
        """PENDING is a valid status per the spec — row must not be skipped."""
        row = self._valid_row(status="PENDING")
        _, ok = self._parse(row)
        assert ok is True

    def test_failed_status_accepted(self):
        row = self._valid_row(status="FAILED")
        record, ok = self._parse(row)
        assert ok is True
        assert record["status"] == "FAILED"

    def test_amount_zero_accepted(self):
        """KYC events legitimately have amount=0.0."""
        row = self._valid_row(product="KYC", event_type="TIER_UPGRADE", amount="0.0")
        record, ok = self._parse(row)
        assert ok is True
        assert record["amount"] == Decimal("0.00")


# ── ActivityCreate schema unit tests ─────────────────────────────────────────

class TestActivityCreateSchema:
    """Direct schema validation tests."""

    def _base_data(self) -> dict:
        return {
            "event_id": uuid.uuid4(),
            "merchant_id": "MRC-123456",
            "event_timestamp": "2024-06-15T08:30:00",
            "product": "AIRTIME",
            "event_type": "AIRTIME_PURCHASE",
            "amount": "500.00",
            "status": "SUCCESS",
            "channel": "APP",
            "region": "ABUJA",
            "merchant_tier": "STARTER",
        }

    def test_valid_schema_creates_correctly(self):
        data = self._base_data()
        obj = ActivityCreate(**data)
        assert obj.merchant_id == "MRC-123456"
        assert obj.amount == Decimal("500.00")

    def test_amount_string_coercion(self):
        data = self._base_data()
        data["amount"] = "bad_value"
        obj = ActivityCreate(**data)
        assert obj.amount == Decimal("0.00")

    def test_to_db_dict_has_all_keys(self):
        obj = ActivityCreate(**self._base_data())
        db_dict = obj.to_db_dict()
        expected_keys = {
            "event_id", "merchant_id", "event_timestamp", "product",
            "event_type", "amount", "status", "channel", "region", "merchant_tier",
        }
        assert expected_keys == set(db_dict.keys())
