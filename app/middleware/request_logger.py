"""
app/middleware/request_logger.py
=================================
Request/response logging middleware.

Logs a structured entry for every HTTP request that passes through the
application.  This gives us a complete access log without relying on
uvicorn's built-in access logs (which are less structured).

Each log entry includes:
  - HTTP method   (GET, POST, …)
  - URL path      (/api/v1/stocks/RELIANCE.NS)
  - Status code   (200, 404, 500, …)
  - Response time (in milliseconds)
  - Client IP     (from X-Forwarded-For or direct connection)

Usage:
  Registered in main.py:
    app.add_middleware(RequestLoggerMiddleware)

Why BaseHTTPMiddleware?
  Starlette's `BaseHTTPMiddleware` is the simplest way to write middleware
  in Python.  It gives us a `call_next(request)` function that we await
  to get the response, letting us measure timing and log both sides.
"""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

# Paths to EXCLUDE from request logging (avoids spamming logs with health checks)
_EXCLUDED_PATHS: frozenset[str] = frozenset({
    "/health",
    "/favicon.ico",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that logs each HTTP request and its response.

    Adds an `X-Request-Time-Ms` header to every response so clients and
    load balancers can see server-side processing time.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip logging for excluded paths
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        # Record start time BEFORE processing the request
        start_time = time.perf_counter()

        # Extract client IP (respect X-Forwarded-For for requests behind a proxy)
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            # Log failed requests too (exception handlers will convert to HTTP response)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "elapsed_ms": elapsed_ms,
                    "error": str(exc),
                },
            )
            raise

        # Calculate total processing time
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Add timing header to the response
        response.headers["X-Request-Time-Ms"] = str(elapsed_ms)

        # Log at INFO for normal requests, WARNING for slow ones (> 1000ms)
        log_level = logging.WARNING if elapsed_ms > 1000 else logging.INFO
        logger.log(
            log_level,
            "%s %s → %d (%.2fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            client_ip,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "client_ip": client_ip,
            },
        )

        return response
