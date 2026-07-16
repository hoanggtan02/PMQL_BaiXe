"""Domain entity: ParkingSession."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class ParkingSession:
    """Represents one parking entry/exit cycle."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    lane_in_id: str = ""
    lane_out_id: str | None = None
    vehicle_id: str | None = None
    plate_number: str = ""
    rfid_card_id: str | None = None
    subscriber_id: str | None = None  # if not None → fee = 0 (check validity in use case)
    shift_id: str | None = None
    entry_time: datetime = field(default_factory=datetime.utcnow)
    exit_time: datetime | None = None
    fee_rule_id: str | None = None
    fee_amount: int = 0  # VND — ALWAYS int, NEVER float
    status: str = "ACTIVE"  # 'ACTIVE' | 'CLOSED' | 'EXCEPTION'
    entry_plate_image_path: str | None = None
    exit_plate_image_path: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1

    def close(self, exit_time: datetime, fee_amount: int, lane_out_id: str) -> None:
        """Close the session after vehicle exits."""
        self.exit_time = exit_time
        self.fee_amount = fee_amount
        self.lane_out_id = lane_out_id
        self.status = "CLOSED"
        self.updated_at = datetime.utcnow()
        self.sync_version += 1
