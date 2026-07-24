"""
tests/conftest.py
==================
pytest fixtures shared across the entire test suite.

This file is automatically loaded by pytest before any test runs.
Fixtures defined here are available to ALL tests without importing.

Key fixtures:
  - app       → The FastAPI application instance (test configuration)
  - client    → Async HTTP test client (httpx.AsyncClient)
  - db        → Async database session connected to the test database
  - override_settings → Temporarily override Settings values in tests

Environment:
  Tests use a separate test database to avoid touching development data.
  Set TEST_DATABASE_URL in your environment before running tests:
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/finpulse_test"

Running tests:
    pytest                          ← run all tests
    pytest tests/test_health.py     ← run a specific file
    pytest -v -k "test_stock"       ← run tests matching keyword
    pytest --asyncio-mode=auto      ← run with auto async mode
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import create_app
from app.config import get_settings, Settings


# ------------------------------------------------------------------------------
# pytest-asyncio configuration
# ------------------------------------------------------------------------------

# Tell pytest-asyncio to treat all async tests as async automatically
# (without needing @pytest.mark.asyncio on each one)
pytest_plugins = ["pytest_asyncio"]


# ------------------------------------------------------------------------------
# Application fixture
# ------------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Return a Settings instance configured for testing.

    Uses a test database URL and disables the scheduler to prevent
    background jobs from running during tests.
    """
    # Override settings for the test environment
    # In a real setup, set TEST_DATABASE_URL as an env var
    get_settings.cache_clear()
    settings = Settings(
        APP_ENV="development",
        DEBUG=True,
        SCHEDULER_ENABLED=False,    # Disable scheduler during tests
        LOG_LEVEL="WARNING",        # Reduce log noise during tests
        # DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/finpulse_test",
    )
    return settings


@pytest.fixture(scope="session")
def app(test_settings: Settings):
    """
    Create a test FastAPI application instance.

    Uses session scope so the app is created once for the entire test run
    (faster than recreating it for every test).
    """
    return create_app()


# ------------------------------------------------------------------------------
# HTTP client fixture
# ------------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def client(app) -> AsyncClient:
    """
    Async HTTP test client for making requests to the FastAPI app.

    Uses httpx.AsyncClient with ASGITransport so no real HTTP server
    needs to be started — requests go directly to the ASGI app.

    Usage in tests:
        async def test_health(client: AsyncClient):
            response = await client.get("/health")
            assert response.status_code == 200
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ------------------------------------------------------------------------------
# Database session fixture (stub — complete when test DB is set up)
# ------------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db():
    """
    Async database session for tests.

    TODO: Implement when models are defined.
    This will:
      1. Create all tables in the test database
      2. Yield an async session
      3. Roll back all changes after each test (keeps tests isolated)

    Usage in tests:
        async def test_create_company(db: AsyncSession):
            company = await company_repo.create(db, ticker="RELIANCE.NS", ...)
            assert company.id is not None
    """
    # TODO: Implement with test DB setup
    yield None
