"""
core/config.py
──────────────────────────────────────────────────────────────────────────────
Application configuration loaded once from the .env file.

Design pattern: Singleton via @lru_cache so the Settings object is constructed
exactly once per process, no matter how many modules import `get_settings()`.

DSA note: Using functools.lru_cache(maxsize=None) gives O(1) lookup after the
first call — cheap hash on the zero-arg call signature.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, resolved from environment / .env file."""

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str

    # ── Server ───────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    debug: bool = False

    # ── Data Import ──────────────────────────────────────────────────────────
    data_dir: str = "./data"
    import_batch_size: int = 5_000

    # ── Testing ──────────────────────────────────────────────────────────────
    test_database_url: str = "sqlite+aiosqlite:///:memory:"
    test_api_port: int = 8080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("data_dir", mode="before")
    @classmethod
    def resolve_data_dir(cls, v: str) -> str:
        """Expand relative paths to absolute at config-load time."""
        return str(Path(v).resolve())

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL for Alembic (psycopg2 driver)."""
        return self.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.

    Using @lru_cache guarantees a single construction per process even under
    concurrent asyncio tasks — CPython's GIL protects the first-call race.
    """
    return Settings()
