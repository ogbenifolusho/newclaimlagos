"""
Security headers and simple in-memory rate limiting for VPS deployment.
"""

import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS only meaningful behind HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple per-IP sliding window. For production at scale, move to Redis.
    Defaults: 120 requests / 60 seconds per IP (auth endpoints tighter).
    """

    def __init__(self, app, requests_per_minute: int = 120, auth_per_minute: int = 20):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.auth_per_minute = auth_per_minute
        self.hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client = request.client.host if request.client else "unknown"
        path = request.url.path
        now = time.time()
        window = 60.0
        limit = self.auth_per_minute if "/auth/" in path else self.requests_per_minute

        # prune
        self.hits[client] = [t for t in self.hits[client] if now - t < window]
        if len(self.hits[client]) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
                headers={"Retry-After": "60"},
            )
        self.hits[client].append(now)
        return await call_next(request)
