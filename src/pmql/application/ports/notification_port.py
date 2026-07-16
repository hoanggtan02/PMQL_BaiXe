"""Application Port: INotificationPort."""

from __future__ import annotations

from abc import ABC, abstractmethod


class INotificationPort(ABC):
    """Send in-app notifications to the operator."""

    @abstractmethod
    async def notify(
        self,
        title: str,
        message: str,
        severity: str = "INFO",  # 'INFO' | 'WARNING' | 'ERROR'
    ) -> None: ...
