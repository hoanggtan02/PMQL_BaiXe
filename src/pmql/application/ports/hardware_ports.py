"""Application Ports: Hardware interfaces."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PlateDetectionResult:
    plate_number: str
    confidence: float
    bounding_box: tuple[int, int, int, int] | None = None
    needs_manual_confirm: bool = False


@dataclass
class CardReadResult:
    rfid_code: str
    raw_bytes: bytes | None = None


class ICameraSource(ABC):
    @abstractmethod
    async def capture_frame(self) -> bytes: ...
    @abstractmethod
    async def start(self) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...


class IANPREngine(ABC):
    @abstractmethod
    async def detect(self, frame: bytes) -> list[PlateDetectionResult]: ...


class ICardReader(ABC):
    @abstractmethod
    async def start(self) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def read_card(self, timeout_sec: float = 5.0) -> CardReadResult | None: ...


class IBarrierController(ABC):
    @abstractmethod
    async def open(self) -> None: ...
    @abstractmethod
    async def close(self) -> None: ...
    @abstractmethod
    async def get_status(self) -> str: ...
