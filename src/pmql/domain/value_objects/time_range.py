"""Value Object: TimeRange."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"TimeRange end ({self.end}) must be >= start ({self.start})")

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)
