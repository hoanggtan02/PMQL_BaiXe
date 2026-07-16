"""Domain entity: Shift (operator work shift)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Shift:
    """Operator work shift with revenue summary."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    operator_id: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    total_sessions: int = 0
    total_revenue: int = 0      # VND — ALWAYS int, NEVER float
    status: str = "OPEN"        # 'OPEN' | 'CLOSED'
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1

    def close(self, end_time: datetime, total_sessions: int, total_revenue: int) -> None:
        """Close the shift and record summary."""
        self.end_time = end_time
        self.total_sessions = total_sessions
        self.total_revenue = total_revenue
        self.status = "CLOSED"
        self.updated_at = datetime.utcnow()
        self.sync_version += 1
