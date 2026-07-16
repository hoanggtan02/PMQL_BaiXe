"""Application Ports: Hardware interfaces.

These ABCs define what hardware adapters must provide.
Use cases depend on these interfaces, never on concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PlateDetectionResult:
    """Result from ANPR pipeline."""

    plate_number: str
    confidence: float       # 0.0–1.0
    bounding_box: tuple[int, int, int, int] | None = None   # (x, y, w, h)
    needs_manual_confirm: bool = False   # True when confidence < threshold


@dataclass
class CardReadResult:
    """Result from RFID card reader."""

    rfid_code: str
    raw_bytes: bytes | None = None


class ICameraSource(ABC):
    """Provides video frames for ANPR."""

    @abstractmethod
    async def capture_frame(self) -> bytes:
        """Return one JPEG/PNG frame as bytes."""
        ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...


class IANPREngine(ABC):
    """License plate recognition pipeline."""

    @abstractmethod
    async def detect(self, frame: bytes) -> list[PlateDetectionResult]:
        """Detect and read all plates in the given frame."""
        ...


class ICardReader(ABC):
    """RFID card reader (Wiegand or similar)."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def read_card(self, timeout_sec: float = 5.0) -> CardReadResult | None:
        """Block until a card is read or timeout expires."""
        ...


class IBarrierController(ABC):
    """Controls the physical boom barrier gate."""

    @abstractmethod
    async def open(self) -> None:
        """Raise the barrier."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Lower the barrier."""
        ...

    @abstractmethod
    async def get_status(self) -> str:
        """Return 'OPEN' | 'CLOSED' | 'MOVING' | 'ERROR'."""
        ...
