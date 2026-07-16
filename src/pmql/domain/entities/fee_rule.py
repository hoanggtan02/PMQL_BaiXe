"""Domain entity: FeeRule — pricing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class FeeRule:
    """Pricing rule applied to a parking session."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    name: str = ""
    vehicle_type: str = ""          # 'motorbike' | 'car' | 'truck'
    free_minutes: int = 10          # grace period — no charge if duration <= this
    block_minutes: int = 60         # billing block size in minutes
    price_per_block: int = 5000     # VND per block — ALWAYS int, NEVER float
    day_max: int | None = None      # max fee per calendar day (VND) — None = unlimited
    night_surcharge: int | None = None  # extra fee for sessions overlapping night hours (VND)
    night_start_hour: int = 22      # night starts at 22:00
    night_end_hour: int = 6         # night ends at 06:00 next day
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
