"""
api/router.py
──────────────────────────────────────────────────────────────────────────────
Central router that aggregates all domain sub-routers.
"""
from fastapi import APIRouter

from src.modules.analytics.api.router import router as analytics_router
from src.modules.health.api.router import router as health_router

api_router = APIRouter()
api_router.include_router(analytics_router)
api_router.include_router(health_router)
