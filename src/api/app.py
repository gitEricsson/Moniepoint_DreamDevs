"""
api/app.py
──────────────────────────────────────────────────────────────────────────────
FastAPI application factory.

Design pattern: Factory + Module-level Singleton.
  `create_app()` builds the FastAPI instance once and caches it in `_app`.
  Subsequent calls return the same object — useful for test overrides while
  preventing accidental double-initialisation in production.
"""
from __future__ import annotations

from fastapi import FastAPI

from src.api.router import api_router
from src.core.config import get_settings
from src.core.logging_setup import setup_logging
from src.middleware.cors_middleware import setup_cors
from src.middleware.error_handler import register_error_handlers
from src.middleware.security_middleware import SecurityHeadersMiddleware
from src.middleware.timing_middleware import TimingMiddleware
from src.middleware.logging_middleware import LoggingMiddleware
from src.tasks.import_task import lifespan

# ── Singleton guard ───────────────────────────────────────────────────────────
_app: FastAPI | None = None


def create_app() -> FastAPI:
    """
    Build (or return the cached) FastAPI application.

    Registers:
      • Lifespan handler      — CSV import on startup
      • Request logging       — method / path / status / latency
      • Global error handlers — consistent JSON error envelope
      • API router            — all /analytics endpoints
    """
    global _app
    if _app is not None:
        return _app

    setup_logging()
    settings = get_settings()

    application = FastAPI(
        title="Moniepoint Analytics API",
        description=(
            "Processes merchant activity logs and exposes key business "
            "insights for the Growth & Intelligence team."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Analytics", "description": "Endpoints to calculate massive merchant scale analytics"},
            {"name": "Health", "description": "Operations status checks"},
        ]
    )

    # Cross-Origin
    setup_cors(application)

    # Middleware (outermost first)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(TimingMiddleware)
    application.add_middleware(LoggingMiddleware)

    # Exception handlers
    register_error_handlers(application)

    # Routes
    application.include_router(api_router)

    _app = application
    return _app
