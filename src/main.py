"""
main.py
──────────────────────────────────────────────────────────────────────────────
Application entry point.

Run with:
    python -m src.main
    # or directly:
    uvicorn src.main:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import uvicorn

from src.api.app import create_app
from src.core.config import get_settings

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info",
    )
