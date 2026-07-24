"""
app/repositories/__init__.py
=============================
Repository (data access) layer package.

Repositories are the ONLY layer allowed to execute SQL queries.
They abstract the database away from the service layer so that:
  - Business logic doesn't know or care about SQL
  - Database queries can be tested in isolation
  - Switching from PostgreSQL to another DB only affects this layer

Each model should have one corresponding repository:
    Company      → CompanyRepository
    MarketData   → MarketDataRepository
    HistoricalPrice → HistoricalPriceRepository

All repositories inherit from BaseRepository (base_repository.py).
"""
