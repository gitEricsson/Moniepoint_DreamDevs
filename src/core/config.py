from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    database_url: str

    api_host: str = "0.0.0.0"
    api_port: int = 8080
    debug: bool = False

    data_dir: str = "./data"
    import_batch_size: int = 5_000

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
        return str(Path(v).resolve())

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://"
        )

@lru_cache(maxsize=None)
def get_settings() -> Settings:
    return Settings()
