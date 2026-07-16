"""Domain entity: Vehicle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Vehicle:
    """Represents a registered vehicle."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    plate_number: str = ""
    vehicle_type: str = ""  # 'motorbike' | 'car' | 'truck'
    rfid_tag: str | None = None
    subscriber_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
