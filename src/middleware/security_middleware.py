"""
middleware/security_middleware.py
──────────────────────────────────────────────────────────────────────────────
Adds strict HTTP security headers to all outbound responses.
"""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Prevent browsers from MIME-sniffing a response away from the declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking by forbidding iframe embedding
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable browser XSS filtering
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Enforce HTTPS-only routing (HSTS) for 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Restrict how much referrer information should be included with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
