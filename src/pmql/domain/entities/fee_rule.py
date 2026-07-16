"""Domain entity: FeeRule — pricing configuration."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class FeeRule:
    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    name: str = ""
    vehicle_type: str = ""
    free_minutes: int = 10
    block_minutes: int = 60
    price_per_block: int = 5000
    day_max: int | None = None
    night_surcharge: int | None = None
    night_start_hour: int = 22
    night_end_hour: int = 6
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
