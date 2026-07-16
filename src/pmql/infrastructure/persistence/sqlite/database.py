"""Local SQLite engine + session factory.

Single place that owns the async engine so the rest of the app never
imports SQLAlchemy engine internals directly.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from pmql.infrastructure.persistence.sqlite.models import Base


class Database:
    """Owns the engine + sessionmaker for the local branch database."""

    def __init__(self, database_url: str) -> None:
        # Ensure the SQLite file's parent directory exists (e.g. ./data/)
        if database_url.startswith("sqlite"):
            path_part = database_url.split("///")[-1]
            if path_part not in (":memory:", ""):
                Path(path_part).parent.mkdir(parents=True, exist_ok=True)

        self.engine: AsyncEngine = create_async_engine(database_url, echo=False, future=True)
        self._sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_all(self) -> None:
        """Create tables if they don't exist yet.

        NOTE: this is a bootstrap convenience for local dev only. Real
        schema evolution in production should go through Alembic
        migrations, not `create_all`.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session wrapped in a transaction (commit on success, rollback on error)."""
        async with self._sessionmaker() as session:
            async with session.begin():
                yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
