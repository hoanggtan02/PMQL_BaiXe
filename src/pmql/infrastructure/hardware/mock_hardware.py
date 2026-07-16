"""Mock hardware adapters."""
from __future__ import annotations
import structlog
from pmql.application.ports.hardware_ports import CardReadResult, PlateDetectionResult

log = structlog.get_logger(__name__)


class MockBarrierController:
    def __init__(self) -> None:
        self._status = "CLOSED"

    async def open(self) -> None:
        self._status = "OPEN"
        log.info("mock_barrier.open")

    async def close(self) -> None:
        self._status = "CLOSED"
        log.info("mock_barrier.close")

    async def get_status(self) -> str:
        return self._status


class MockCardReader:
    def __init__(self) -> None:
        self._next_code: str | None = None

    def simulate_scan(self, rfid_code: str) -> None:
        self._next_code = rfid_code

    async def start(self) -> None:
        log.info("mock_card_reader.start")

    async def stop(self) -> None:
        log.info("mock_card_reader.stop")

    async def read_card(self, timeout_sec: float = 5.0) -> CardReadResult | None:
        if self._next_code is None:
            return None
        code, self._next_code = self._next_code, None
        return CardReadResult(rfid_code=code)


class MockCameraSource:
    async def start(self) -> None:
        log.info("mock_camera.start")

    async def stop(self) -> None:
        log.info("mock_camera.stop")

    async def capture_frame(self) -> bytes:
        return b""


class MockANPREngine:
    def __init__(self) -> None:
        self._next_plate: str | None = None

    def simulate_plate(self, plate_number: str, confidence: float = 0.95) -> None:
        self._next_plate = plate_number
        self._confidence = confidence

    async def detect(self, frame: bytes) -> list[PlateDetectionResult]:
        if self._next_plate is None:
            return []
        result = [
            PlateDetectionResult(
                plate_number=self._next_plate,
                confidence=self._confidence,
                needs_manual_confirm=self._confidence < 0.75,
            )
        ]
        self._next_plate = None
        return result
