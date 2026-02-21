"""
middleware/logging_middleware.py
──────────────────────────────────────────────────────────────────────────────
Logs incoming requests with URL and status resolution.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging_setup import get_logger

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "%s %s → %d  [%.1f ms]",
            request.method,
            request.url.path,
            response.status_code,
            process_time_ms,
        )
        return response
