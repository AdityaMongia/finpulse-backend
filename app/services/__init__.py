"""
app/services/__init__.py
=========================
Business logic (service) layer package.

Services are the heart of the application.  They:
  - Orchestrate one or more repositories to fulfill a use case
  - Enforce business rules (e.g., "don't fetch data for delisted companies")
  - Call external APIs (via yfinance_client.py) when needed
  - Are completely independent of HTTP (no Request/Response objects here)

Dependency flow:
  API route handler
      ↓ (injects via Depends)
  Service
      ↓ (injects via constructor)
  Repository
      ↓ (executes queries via)
  AsyncSession → PostgreSQL
"""
