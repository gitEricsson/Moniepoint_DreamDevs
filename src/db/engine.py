"""
db/engine.py
──────────────────────────────────────────────────────────────────────────────
Async SQLAlchemy engine — created once at module import time.

Design pattern: Module-level Singleton.
  The `_engine` variable is assigned exactly once per Python process.  All
  callers that import `engine` share the same connection pool, avoiding the
  overhead of creating multiple pools.

Performance notes:
  • pool_size=10  — steady-state concurrency target
  • max_overflow=20 — burst headroom above pool_size
  • pool_pre_ping=True — drops stale connections before use (resilience)
  • echo=False — disable SQL logging in production (set DEBUG=true for dev)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.config import get_settings


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.debug,
        future=True,
    )


# ── Singleton engine ──────────────────────────────────────────────────────────
engine: AsyncEngine = _build_engine()
