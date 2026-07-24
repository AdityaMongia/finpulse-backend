"""
app/repositories/base_repository.py
=====================================
Generic async base repository with standard CRUD operations.

Design
------
BaseRepository is a generic class parameterised by the ORM model type `T`.
Concrete repositories inherit from it and gain all CRUD methods automatically:

    class CompanyRepository(BaseRepository[Company]):
        # get_by_id, get_all, create, update, delete already available
        # Add custom queries specific to Company here:
        async def get_by_ticker(self, ticker: str) -> Company | None:
            ...

Dependency Injection
--------------------
Repositories are NOT singletons.  A new repository instance is created per
request and receives the request-scoped database session via the constructor.
This is called Constructor Injection — a core pattern in Clean Architecture.

    # In a service:
    def __init__(self, db: AsyncSession):
        self.company_repo = CompanyRepository(db)

Why not a global session?
    A global session would share state across requests, leading to race
    conditions and stale data.  Each request must get its own isolated session.

Type variables
--------------
    T  → The SQLAlchemy model class (e.g., Company)
    ID → The type of the primary key (default: int)
"""

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

logger = logging.getLogger(__name__)

# Generic type variables
T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic async repository providing standard CRUD operations.

    Parameters
    ----------
    model : type[T]
        The SQLAlchemy ORM model class this repository manages.
    db : AsyncSession
        The async database session for this request.
    """

    def __init__(self, model: type[T], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    async def get_by_id(self, record_id: int) -> T | None:
        """
        Fetch a single record by primary key.

        Returns None (not an exception) if not found — let the service
        layer decide whether to raise NotFoundError.
        """
        result = await self.db.execute(
            select(self.model).where(self.model.id == record_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """
        Fetch a paginated list of all records.

        Parameters
        ----------
        offset : int
            Number of records to skip (for pagination).
        limit : int
            Maximum number of records to return (max 100).
        """
        result = await self.db.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return the total number of records in the table."""
        result = await self.db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def exists(self, record_id: int) -> bool:
        """Return True if a record with the given ID exists."""
        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.id == record_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one() > 0

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    async def create(self, **kwargs: Any) -> T:
        """
        Create and persist a new record.

        Parameters
        ----------
        **kwargs
            Column values for the new record.

        Returns the newly created ORM instance (with auto-generated ID).
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()   # Flush to DB to get generated ID (no commit yet)
        await self.db.refresh(instance)  # Reload from DB (picks up server defaults)
        logger.debug("Created %s id=%s", self.model.__name__, instance.id)  # type: ignore[attr-defined]
        return instance

    async def update(self, record_id: int, **kwargs: Any) -> T | None:
        """
        Update specific fields on an existing record.

        Parameters
        ----------
        record_id : int
            Primary key of the record to update.
        **kwargs
            Fields to update and their new values.

        Returns the updated record, or None if not found.
        """
        instance = await self.get_by_id(record_id)
        if instance is None:
            return None

        for field, value in kwargs.items():
            setattr(instance, field, value)

        await self.db.flush()
        await self.db.refresh(instance)
        logger.debug("Updated %s id=%s", self.model.__name__, record_id)
        return instance

    async def delete(self, record_id: int) -> bool:
        """
        Delete a record by primary key.

        Returns True if a record was deleted, False if not found.
        """
        result = await self.db.execute(
            delete(self.model).where(self.model.id == record_id)  # type: ignore[attr-defined]
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.debug("Deleted %s id=%s", self.model.__name__, record_id)
        return deleted

    # ------------------------------------------------------------------
    # Protected helpers for subclasses
    # ------------------------------------------------------------------

    async def _execute_query(self, query: Select) -> list[T]:
        """
        Execute a custom SELECT query and return a list of model instances.
        Use this in subclasses to avoid boilerplate.

        Example (in CompanyRepository):
            query = select(Company).where(Company.exchange == "NSE")
            return await self._execute_query(query)
        """
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _execute_scalar(self, query: Select) -> Any:
        """
        Execute a query and return a single scalar value.
        Useful for aggregates (COUNT, SUM, MAX, etc.).
        """
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
