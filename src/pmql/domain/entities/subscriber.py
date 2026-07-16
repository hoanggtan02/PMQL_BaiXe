"""Domain entity: Subscriber (monthly pass holder)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import uuid4


@dataclass
class Subscriber:
    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    full_name: str = ""
    phone: str = ""
    email: str | None = None
    vehicle_type: str = ""
    valid_from: date = field(default_factory=date.today)
    valid_until: date = field(default_factory=date.today)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1

    @property
    def is_valid_today(self) -> bool:
        today = date.today()
        return self.is_active and self.valid_from <= today <= self.valid_until
