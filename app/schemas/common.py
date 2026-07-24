"""
app/schemas/common.py
=====================
Shared Pydantic schema building blocks used across multiple endpoints.

Contains:
  - Base schema configuration
  - Paginated response wrapper
  - Standard health/status response
  - Generic success/error envelope

These schemas avoid duplication by being reused in endpoint-specific schemas.

Usage:
    from app.schemas.common import PaginatedResponse, HealthResponse
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# TypeVar for generic PaginatedResponse
T = TypeVar("T")


# ------------------------------------------------------------------------------
# Base configuration
# ------------------------------------------------------------------------------

class FinPulseBaseModel(BaseModel):
    """
    Base model for all FinPulse Pydantic schemas.

    Configures:
      - from_attributes=True: allows building from ORM objects (sqlalchemy models)
      - populate_by_name=True: allows using field name OR alias
      - str_strip_whitespace: auto-strip leading/trailing whitespace from strings
    """

    model_config = ConfigDict(
        from_attributes=True,       # ORM mode: can build from SQLAlchemy model instances
        populate_by_name=True,      # Accept both alias and field name in input
        str_strip_whitespace=True,  # Strip accidental whitespace in string fields
    )


# ------------------------------------------------------------------------------
# Pagination
# ------------------------------------------------------------------------------

class PaginationMeta(FinPulseBaseModel):
    """Pagination metadata included in paginated list responses."""

    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")
    total_items: int = Field(..., ge=0, description="Total number of matching items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class PaginatedResponse(FinPulseBaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Usage:
        class StockListResponse(PaginatedResponse[StockResponse]):
            pass

        # Or directly:
        return PaginatedResponse[StockResponse](
            items=[...],
            pagination=PaginationMeta(page=1, page_size=20, total_items=100, total_pages=5)
        )
    """

    items: list[T] = Field(..., description="List of items for the current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


# ------------------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------------------

class HealthResponse(FinPulseBaseModel):
    """Response schema for the /health endpoint."""

    status: str = Field(..., examples=["healthy"])
    app: str = Field(..., examples=["FinPulse"])
    version: str = Field(..., examples=["0.1.0"])
    environment: str = Field(..., examples=["production"])


# ------------------------------------------------------------------------------
# Generic success / error envelopes
# ------------------------------------------------------------------------------

class SuccessResponse(FinPulseBaseModel):
    """
    Generic success response for operations that don't return data.
    E.g., DELETE operations, background job triggers.
    """

    success: bool = True
    message: str = Field(..., examples=["Operation completed successfully."])


class ErrorDetail(FinPulseBaseModel):
    """A single field-level error detail (used inside ErrorResponse)."""

    field: str | None = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Human-readable error description")
    type: str | None = Field(None, description="Error type code (e.g., 'missing', 'too_small')")


class ErrorResponse(FinPulseBaseModel):
    """
    Structured error response envelope.

    This matches the shape returned by our exception handlers so clients
    can always expect the same JSON structure on error.
    """

    error: dict = Field(
        ...,
        examples=[{"type": "NotFoundError", "detail": "Company 'XYZ' not found."}],
    )
