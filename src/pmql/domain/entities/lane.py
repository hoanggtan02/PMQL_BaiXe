"""Domain entity: Lane."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Lane:
    """Entry or exit lane at the parking facility."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    name: str = ""
    direction: str = "IN"           # 'IN' | 'OUT' | 'BIDIRECTIONAL'
    camera_source: str | None = None    # RTSP URL or USB index string
    rfid_device_id: str | None = None
    barrier_device_id: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
