"""
app/core/exceptions.py
======================
Custom exception hierarchy for FinPulse.

Design principles:
  - All domain exceptions inherit from a single `FinPulseException` base.
  - Each exception carries a human-readable `detail` message and an HTTP
    status code — this keeps exception_handlers.py simple.
  - Raising a domain exception anywhere in the service/repository layer
    will automatically be caught and converted to the correct HTTP response
    by the registered exception handlers.

Usage:
    from app.core.exceptions import NotFoundError, ExternalServiceError

    raise NotFoundError(resource="Company", identifier="INVALID.NS")
    raise ExternalServiceError(service="yFinance", detail="Rate limit exceeded")
"""

from typing import Any


class FinPulseException(Exception):
    """
    Base exception for all FinPulse domain errors.

    Attributes
    ----------
    status_code : int
        The HTTP status code to return to the client.
    detail : str
        Human-readable error message safe to expose in API responses.
    """

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None, **kwargs: Any) -> None:
        self.detail = detail or self.__class__.detail
        # Store any extra context (e.g., ticker, company_id) for logging
        self.context: dict[str, Any] = kwargs
        super().__init__(self.detail)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code}, "
            f"detail={self.detail!r}, "
            f"context={self.context})"
        )


# ------------------------------------------------------------------------------
# 4xx — Client Errors
# ------------------------------------------------------------------------------

class NotFoundError(FinPulseException):
    """
    Raised when a requested resource does not exist in the database.

    Example:
        raise NotFoundError(resource="Company", identifier="INVALID.NS")
    """

    status_code = 404
    detail = "The requested resource was not found."

    def __init__(
        self,
        resource: str = "Resource",
        identifier: Any = None,
        detail: str | None = None,
    ) -> None:
        resolved_detail = detail or f"{resource} '{identifier}' was not found."
        super().__init__(detail=resolved_detail, resource=resource, identifier=identifier)


class ValidationError(FinPulseException):
    """
    Raised when input data fails domain-level validation (beyond Pydantic).

    Note: Pydantic validation errors are handled separately by FastAPI.
    This is for business-rule violations (e.g., "date range exceeds 5 years").

    Example:
        raise ValidationError("Date range cannot exceed 5 years.")
    """

    status_code = 422
    detail = "Validation failed."


class ConflictError(FinPulseException):
    """
    Raised when an operation would violate a uniqueness constraint.

    Example:
        raise ConflictError(resource="Company", identifier="RELIANCE.NS")
    """

    status_code = 409
    detail = "A conflict occurred with the current state of the resource."

    def __init__(
        self,
        resource: str = "Resource",
        identifier: Any = None,
        detail: str | None = None,
    ) -> None:
        resolved_detail = detail or f"{resource} '{identifier}' already exists."
        super().__init__(detail=resolved_detail, resource=resource, identifier=identifier)


class UnauthorizedError(FinPulseException):
    """Raised when authentication credentials are missing or invalid."""

    status_code = 401
    detail = "Authentication required."


class ForbiddenError(FinPulseException):
    """Raised when an authenticated user lacks permission for an action."""

    status_code = 403
    detail = "You do not have permission to perform this action."


# ------------------------------------------------------------------------------
# 5xx — Server / External Errors
# ------------------------------------------------------------------------------

class ExternalServiceError(FinPulseException):
    """
    Raised when a call to an external API (e.g., yFinance) fails.

    Example:
        raise ExternalServiceError(service="yFinance", detail="Rate limit exceeded.")
    """

    status_code = 502
    detail = "An external service returned an unexpected response."

    def __init__(
        self,
        service: str = "External Service",
        detail: str | None = None,
    ) -> None:
        resolved_detail = detail or f"{service} is currently unavailable."
        super().__init__(detail=resolved_detail, service=service)


class DatabaseError(FinPulseException):
    """
    Raised when a database operation fails for an unexpected reason.

    SQLAlchemy exceptions are caught in the repository layer and wrapped
    in this exception before propagating to service / API layers.
    """

    status_code = 500
    detail = "A database error occurred. Please try again later."


class SchedulerError(FinPulseException):
    """Raised when a scheduled job encounters an unrecoverable error."""

    status_code = 500
    detail = "A background scheduler error occurred."
