"""
tasks/import_task.py
──────────────────────────────────────────────────────────────────────────────
FastAPI lifespan startup task that triggers the CSV → DB import.

Runs the import in a ThreadPoolExecutor so it does not block the asyncio event
loop during the synchronous CSV I/O portions.  The actual DB writes are still
fully async.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.core.logging_setup import get_logger
from src.db.session import AsyncSessionFactory
from src.modules.importer.services.import_service import CSVImportService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    All code before `yield` runs at startup; all code after runs at shutdown.
    """
    logger.info("Application starting up — running CSV import check …")

    # Run import asynchronously without blocking other startup tasks
    asyncio.create_task(_run_import())

    yield  # ── Application is live from here ──────────────────────────────────

    logger.info("Application shutting down.")


async def _run_import() -> None:
    """Execute the CSV import pipeline using a fresh database session."""
    try:
        async with AsyncSessionFactory() as session:
            service = CSVImportService(db=session)
            summary = await service.run()

            if summary.already_loaded:
                logger.info("Data already present — import skipped.")
            else:
                logger.info(
                    "Import finished: files=%d  inserted=%d  skipped=%d",
                    summary.files_processed,
                    summary.rows_inserted,
                    summary.rows_skipped,
                )
    except Exception as exc:
        logger.exception("Import task failed: %s", exc)
