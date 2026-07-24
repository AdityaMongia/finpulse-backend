"""
app/api/__init__.py
====================
API layer package.

This package contains everything related to HTTP handling:
  - Route handlers (thin controllers in v1/)
  - Shared FastAPI dependencies (deps.py)
  - Master router aggregation (router.py)

What belongs here:
  ✓ Request parsing and response serialisation
  ✓ Input validation (via Pydantic schemas)
  ✓ Calling services
  ✓ Returning HTTP responses with correct status codes

What does NOT belong here:
  ✗ Business logic
  ✗ SQL queries
  ✗ External API calls
"""
