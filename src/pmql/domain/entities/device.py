"""Domain entity: Device (hardware peripheral)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Device:
    """Hardware device registered in the system."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    name: str = ""
    device_type: str = ""           # 'CAMERA' | 'RFID' | 'BARRIER' | 'FINGERPRINT'
    connection_string: str = ""     # COM port, RTSP URL, IP address, etc.
    is_online: bool = False
    last_seen_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
