"""
db/session.py
──────────────────────────────────────────────────────────────────────────────
Async session factory and FastAPI dependency for database access.

Usage in controllers/services:
    from src.db.session import get_db
    ...
    async def endpoint(db: AsyncSession = Depends(get_db)):
        ...
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.engine import engine


# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep attributes accessible after commit
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a fresh AsyncSession per request and
    ensures it is closed (and rolled back on error) when the request ends.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
