"""Domain entity: Card (RFID)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Card:
    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    rfid_code: str = ""
    subscriber_id: str | None = None
    vehicle_id: str | None = None
    is_active: bool = True
    issued_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
