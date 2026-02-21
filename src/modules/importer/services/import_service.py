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

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = ActivityRepository(db)
        self._settings = get_settings()

    async def run(self) -> ImportSummary:
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

    def _discover_csv_files(self) -> list[Path]:
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
        raw_event_id = raw.get("event_id", "").strip()
        if not raw_event_id:
            return None, False

        try:
            event_id = uuid.UUID(raw_event_id)
        except ValueError:
            return None, False

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
