"""Local SQLite engine + session factory."""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from pmql.infrastructure.persistence.sqlite.models import Base


class Database:
    def __init__(self, database_url: str) -> None:
        if database_url.startswith("sqlite"):
            path_part = database_url.split("///")[-1]
            if path_part not in (":memory:", ""):
                Path(path_part).parent.mkdir(parents=True, exist_ok=True)
        self.engine: AsyncEngine = create_async_engine(database_url, echo=False, future=True)
        self._sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_all(self) -> None:
        async with self.engine.begin() as conn:
            # Lightweight compatibility migration for existing local MVP DBs.
            # Production deployments should move this to Alembic.
            if self.engine.url.get_backend_name() == "sqlite":
                for table in ("lanes", "subscribers", "cards", "fee_rules", "users"):
                    columns = (await conn.execute(text(f"PRAGMA table_info({table})"))).mappings().all()
                    if columns and "is_deleted" not in {column["name"] for column in columns}:
                        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0"))
                # Shift columns migration
                shift_columns = (await conn.execute(text("PRAGMA table_info(shifts)"))).mappings().all()
                if shift_columns:
                    col_names = {column["name"] for column in shift_columns}
                    if "lane_id" not in col_names:
                        await conn.execute(text("ALTER TABLE shifts ADD COLUMN lane_id VARCHAR(36) NULL"))
                    if "note" not in col_names:
                        await conn.execute(text("ALTER TABLE shifts ADD COLUMN note VARCHAR(255) NOT NULL DEFAULT ''"))
                    if "opening_cash" not in col_names:
                        await conn.execute(text("ALTER TABLE shifts ADD COLUMN opening_cash INTEGER NOT NULL DEFAULT 0"))
                    if "closing_cash" not in col_names:
                        await conn.execute(text("ALTER TABLE shifts ADD COLUMN closing_cash INTEGER NOT NULL DEFAULT 0"))
                    if "close_note" not in col_names:
                        await conn.execute(text("ALTER TABLE shifts ADD COLUMN close_note VARCHAR(255) NOT NULL DEFAULT ''"))
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session:
            async with session.begin():
                yield session

    async def dispose(self) -> None:
        await self.engine.dispose()
