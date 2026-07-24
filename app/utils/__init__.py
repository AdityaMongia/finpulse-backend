"""
app/utils/__init__.py
======================
Utility functions package.

Contains pure functions with no side effects and no dependencies on
FastAPI, SQLAlchemy, or any other framework-specific code.

Utilities should be:
  ✓ Pure (same input always produces same output)
  ✓ Independently testable
  ✓ Reusable across any layer (service, repository, scheduler)
  ✗ Not aware of HTTP or database concerns
"""
