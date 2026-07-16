"""Application Port: ISyncOutboxWriter.

Use cases call this port to enqueue records for MySQL sync.
They MUST NOT import anything from infrastructure.persistence.central.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ISyncOutboxWriter(ABC):
    """Write an outbox entry in the same transaction as the business write."""

    @abstractmethod
    async def enqueue(
        self,
        entity_table: str,
        entity_id: str,
        operation: str,         # 'INSERT' | 'UPDATE' | 'DELETE'
        payload: dict[str, object],
    ) -> None:
        """Record a pending sync event.

        Must be called within the same DB transaction as the entity write
        to guarantee atomic consistency.
        """
        ...
