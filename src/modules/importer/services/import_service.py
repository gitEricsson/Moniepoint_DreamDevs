"""
services/import_service.py
──────────────────────────────────────────────────────────────────────────────
CSV → PostgreSQL import pipeline.

Design principles:
  • Streaming: reads files in configurable batches (default 5 000 rows) so
    memory usage is O(batch_size) regardless of file size.
  • Idempotent: uses INSERT ON CONFLICT DO NOTHING at the DB level.
  • In-memory dedup: an event_id `set` provides O(1) duplicate detection
    *within a single import run* before records hit the DB — avoids wasted
    round-trips for intra-file duplicates.
  • Graceful errors: malformed rows (missing fields, bad types) are logged and
    counted but never crash the pipeline.

DSA note on the seen_ids set:
  A Python set uses a hash table internally → O(1) average insert/lookup.
  For 2M rows the set uses ~64 MB RAM (8 bytes per UUID hash slot * 2M * 4
  load-factor overhead), which is acceptable. If memory is constrained a
  Bloom filter could reduce this to ~5 MB at the cost of a tiny false-positive
  rate.
"""
from __future__ import annotations

import csv
import uuid
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.logging_setup import get_logger
from src.modules.importer.repositories.activity_repository import ActivityRepository
from src.modules.importer.schemas.activity import ActivityCreate
from src.modules.analytics.schemas.analytics import ImportSummary

logger = get_logger(__name__)


class CSVImportService:
    """
    Orchestrates discovery, parsing, validation, and bulk loading of all
    activities_YYYYMMDD.csv files found in DATA_DIR.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = ActivityRepository(db)
        self._settings = get_settings()

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(self) -> ImportSummary:
        """
        Execute the full import pipeline.

        Steps:
          1. Check if data already exists (idempotency guard).
          2. Discover CSV files in DATA_DIR.
          3. Stream each file in batches → validate → bulk insert.
          4. Return an ImportSummary for logging.
        """
        existing = await self._repo.count_total()
        if existing > 0:
            logger.info(
                "Import skipped — %d rows already in DB.", existing
            )
            return ImportSummary(
                files_processed=0,
                rows_inserted=0,
                rows_skipped=0,
                already_loaded=True,
            )

        csv_files = self._discover_csv_files()
        if not csv_files:
            logger.warning("No CSV files found in %s", self._settings.data_dir)
            return ImportSummary(files_processed=0, rows_inserted=0, rows_skipped=0)

        logger.info("Found %d CSV file(s) to import.", len(csv_files))

        # ── O(1) per-lookup dedup: hash set of already-seen event UUIDs ──────
        seen_ids: set[uuid.UUID] = set()
        total_inserted = 0
        total_skipped = 0

        for file_path in csv_files:
            inserted, skipped = await self._import_file(
                file_path, seen_ids
            )
            total_inserted += inserted
            total_skipped += skipped
            logger.info(
                "  %s → inserted=%d  skipped=%d",
                file_path.name,
                inserted,
                skipped,
            )

        logger.info(
            "Import complete: files=%d  inserted=%d  skipped=%d",
            len(csv_files),
            total_inserted,
            total_skipped,
        )
        return ImportSummary(
            files_processed=len(csv_files),
            rows_inserted=total_inserted,
            rows_skipped=total_skipped,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _discover_csv_files(self) -> list[Path]:
        """
        Return sorted list of activities_YYYYMMDD.csv paths.
        Sorted by filename ensures deterministic processing order (chronological).
        """
        data_dir = Path(self._settings.data_dir)
        if not data_dir.exists():
            logger.error("DATA_DIR does not exist: %s", data_dir)
            return []
        return sorted(data_dir.glob("activities_*.csv"))

    async def _import_file(
        self,
        file_path: Path,
        seen_ids: set[uuid.UUID],
    ) -> tuple[int, int]:
        """
        Stream one CSV file in batch_size chunks.

        Returns (rows_inserted, rows_skipped) for this file.
        """
        batch_size = self._settings.import_batch_size
        batch: list[dict] = []
        inserted = 0
        skipped = 0

        try:
            with file_path.open(newline="", encoding="utf-8", errors="replace") as fh:
                reader = csv.DictReader(fh)

                for raw_row in reader:
                    record, ok = self._parse_row(raw_row, seen_ids)
                    if not ok:
                        skipped += 1
                        continue

                    seen_ids.add(record["event_id"])
                    batch.append(record)

                    if len(batch) >= batch_size:
                        inserted += await self._repo.bulk_insert(batch)
                        batch.clear()

                # Flush remaining rows
                if batch:
                    inserted += await self._repo.bulk_insert(batch)

        except OSError as exc:
            logger.error("Cannot read file %s: %s", file_path, exc)

        return inserted, skipped

    @staticmethod
    def _parse_row(
        raw: dict[str, str],
        seen_ids: set[uuid.UUID],
    ) -> tuple[dict | None, bool]:
        """
        Validate and convert one raw CSV row.

        Returns (db_dict, True) on success, (None, False) on any error.

        Validation rules:
          • merchant_id must not be blank
          • event_timestamp must not be blank / unparseable
          • amount: non-numeric → coerced to 0.00 (not a skip condition)
          • status/product: unrecognised → skip
          • duplicate event_id (in-process set) → skip
        """
        # ── Guard: empty event_id ─────────────────────────────────────────────
        raw_event_id = raw.get("event_id", "").strip()
        if not raw_event_id:
            return None, False

        try:
            event_id = uuid.UUID(raw_event_id)
        except ValueError:
            return None, False

        # ── In-memory dedup O(1) ─────────────────────────────────────────────
        if event_id in seen_ids:
            return None, False

        try:
            activity = ActivityCreate(
                event_id=event_id,
                merchant_id=raw.get("merchant_id", ""),
                event_timestamp=raw.get("event_timestamp", ""),
                product=raw.get("product", ""),
                event_type=raw.get("event_type", ""),
                amount=raw.get("amount", "0"),
                status=raw.get("status", ""),
                channel=raw.get("channel"),
                region=raw.get("region"),
                merchant_tier=raw.get("merchant_tier"),
            )
            return activity.to_db_dict(), True

        except (ValidationError, ValueError):
            return None, False
