"""Domain entity: Alert."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Alert:
    """System alert or warning for operators."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    alert_type: str = ""    # 'SYNC_FAILURE' | 'HARDWARE_ERROR' | 'WRONG_VEHICLE' | ...
    severity: str = "INFO"  # 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
    message: str = ""
    related_entity_id: str | None = None    # e.g. session id, device id
    is_acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1

    def acknowledge(self, user_id: str) -> None:
        self.is_acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.sync_version += 1
