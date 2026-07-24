"""
migrations/env.py
==================
Alembic migration environment — the most important Alembic file.

This file is executed by Alembic whenever you run any `alembic` command.
It tells Alembic:
  1. Where to find the database (DATABASE_URL from settings)
  2. What tables exist (via Base.metadata from our ORM models)
  3. How to run migrations (async engine for asyncpg)

Key customisations from Alembic's default env.py:
  - Uses `run_async_migrations()` to work with our async engine
  - Imports `Base` from app.database.base so autogenerate finds all models
  - Reads DATABASE_URL from pydantic-settings (not hardcoded in alembic.ini)

How to add a new model to autogenerate:
  1. Create the model in app/models/your_model.py (inheriting from Base)
  2. Import it in app/models/__init__.py
  3. Run: alembic revision --autogenerate -m "add your_model table"
  4. Review the generated migration in migrations/versions/
  5. Apply: alembic upgrade head
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# --- Import our application's Base and models --------------------------------
# Importing Base makes Alembic aware of all table definitions.
# Importing models/__init__.py ensures all model classes are registered
# with Base.metadata (even if they're not used elsewhere in migrations).
from app.database.base import Base
import app.models  # noqa: F401 — ensures all models are registered with Base

# --- Import settings to get the DATABASE_URL ----------------------------------
from app.config import settings

# ---------------------------------------------------------------------------
# Alembic configuration object — wraps the alembic.ini file
# ---------------------------------------------------------------------------
config = context.config

# Set the database URL from our application settings
# This overrides the sqlalchemy.url in alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Setup Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which metadata to use for autogenerate comparison
# Without this, `alembic revision --autogenerate` would generate empty migrations
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration mode (no DB connection required)
# ---------------------------------------------------------------------------
# Used when you want to generate SQL scripts without connecting to the DB:
#   alembic upgrade head --sql

def run_migrations_offline() -> None:
    """Run migrations without connecting to the database (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include schemas in autogenerate (useful for multi-schema setups)
        include_schemas=False,
        # Render column comments in migration scripts
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode (connects to real database)
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    """Execute the actual migration using a synchronous connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Compare column types (detects column type changes in autogenerate)
        compare_type=True,
        # Compare server defaults (detects DEFAULT value changes)
        compare_server_default=True,
        # Include column comments in autogenerate
        include_schemas=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Create an async engine and run migrations.

    We cannot use the module-level `engine` from app.database.engine
    because Alembic needs a sync connection to run migrations.
    We use `run_sync()` to bridge async → sync for the migration step.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No pooling during migrations (one-shot)
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online (connected) migrations."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point — Alembic calls this file directly
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
