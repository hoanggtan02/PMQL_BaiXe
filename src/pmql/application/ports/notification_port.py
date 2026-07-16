"""Application Port: INotificationPort."""
from __future__ import annotations
from abc import ABC, abstractmethod


class INotificationPort(ABC):
    @abstractmethod
    async def notify(self, title: str, message: str, severity: str = "INFO") -> None: ...
