"""SQLite-backed implementation of ISyncOutboxWriter."""
from __future__ import annotations
import json
from sqlalchemy.ext.asyncio import AsyncSession
from pmql.infrastructure.persistence.sqlite.models import SyncOutboxModel


class SQLiteSyncOutboxWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, entity_table: str, entity_id: str, operation: str, payload: dict[str, object]) -> None:
        self._session.add(
            SyncOutboxModel(
                entity_table=entity_table,
                entity_id=entity_id,
                operation=operation,
                payload_json=json.dumps(payload, ensure_ascii=False),
            )
        )
        await self._session.flush()
