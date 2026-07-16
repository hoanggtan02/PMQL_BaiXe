"""Application Port: ISyncOutboxWriter."""
from __future__ import annotations
from abc import ABC, abstractmethod


class ISyncOutboxWriter(ABC):
    @abstractmethod
    async def enqueue(
        self, entity_table: str, entity_id: str, operation: str, payload: dict[str, object]
    ) -> None: ...
