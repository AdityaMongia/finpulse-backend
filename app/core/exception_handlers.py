"""
app/core/exception_handlers.py
================================
FastAPI exception handler registration.

Each handler maps an exception type → HTTP response.  By centralising all
handler registration here we keep main.py thin and make it trivial to add
new exception types in the future.

How it works:
  1. A route raises e.g. `NotFoundError("Company 'XYZ' not found")`
  2. FastAPI catches it and routes it here (via `add_exception_handler`)
  3. We return a structured `JSONResponse` with the correct status code

Usage (in main.py):
    from app.core.exception_handlers import register_exception_handlers
    register_exception_handlers(app)
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    FinPulseException,
    ForbiddenError,
    NotFoundError,
    SchedulerError,
    UnauthorizedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Response helper
# ------------------------------------------------------------------------------

def _error_response(
    status_code: int,
    error_type: str,
    detail: Any,
    request: Request | None = None,
) -> JSONResponse:
    """
    Build a consistent error JSON envelope.

    Every error response from FinPulse has the same shape:
    {
        "error": {
            "type":   "NotFoundError",
            "detail": "Company 'XYZ' was not found.",
            "path":   "/api/v1/stocks/XYZ"   ← optional
        }
    }
    """
    content: dict[str, Any] = {
        "error": {
            "type": error_type,
            "detail": detail,
        }
    }
    if request is not None:
        content["error"]["path"] = str(request.url.path)

    return JSONResponse(status_code=status_code, content=content)


# ------------------------------------------------------------------------------
# Individual handlers
# ------------------------------------------------------------------------------

async def finpulse_exception_handler(
    request: Request, exc: FinPulseException
) -> JSONResponse:
    """Catch-all handler for any FinPulse domain exception."""
    logger.warning(
        "Domain exception raised: %r | path=%s",
        exc,
        request.url.path,
        extra={"context": exc.context},
    )
    return _error_response(
        status_code=exc.status_code,
        error_type=type(exc).__name__,
        detail=exc.detail,
        request=request,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle Starlette/FastAPI HTTPException (e.g., 404 from routing)."""
    logger.info(
        "HTTP exception: status=%d detail=%s path=%s",
        exc.status_code,
        exc.detail,
        request.url.path,
    )
    return _error_response(
        status_code=exc.status_code,
        error_type="HTTPException",
        detail=exc.detail,
        request=request,
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic v2 request body / query param validation errors.

    We reformat the error list into a friendlier structure instead of
    exposing raw Pydantic internals.
    """
    errors = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    logger.info(
        "Request validation failed: path=%s errors=%s",
        request.url.path,
        errors,
    )
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_type="RequestValidationError",
        detail=errors,
        request=request,
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Fallback handler for any unhandled Python exception.

    Logs the full traceback internally but returns a generic message
    to the client so implementation details are never leaked.
    """
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type="InternalServerError",
        detail="An internal server error occurred. Please try again later.",
        request=request,
    )


# ------------------------------------------------------------------------------
# Registration function
# ------------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    Order matters: more specific exceptions must be registered before
    their base classes, otherwise the base-class handler fires first.
    """
    # Domain exceptions (FinPulse-specific)
    app.add_exception_handler(NotFoundError, finpulse_exception_handler)        # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, finpulse_exception_handler)      # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, finpulse_exception_handler)        # type: ignore[arg-type]
    app.add_exception_handler(UnauthorizedError, finpulse_exception_handler)    # type: ignore[arg-type]
    app.add_exception_handler(ForbiddenError, finpulse_exception_handler)       # type: ignore[arg-type]
    app.add_exception_handler(ExternalServiceError, finpulse_exception_handler) # type: ignore[arg-type]
    app.add_exception_handler(DatabaseError, finpulse_exception_handler)        # type: ignore[arg-type]
    app.add_exception_handler(SchedulerError, finpulse_exception_handler)       # type: ignore[arg-type]
    app.add_exception_handler(FinPulseException, finpulse_exception_handler)    # type: ignore[arg-type]

    # Framework-level exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)           # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)  # type: ignore[arg-type]

    # Catch-all (must be last)
    app.add_exception_handler(Exception, unhandled_exception_handler)           # type: ignore[arg-type]
