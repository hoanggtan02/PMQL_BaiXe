"""Value Object: TimeRange."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class TimeRange:
    """Immutable time range between two datetime values."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"TimeRange end ({self.end}) must be >= start ({self.start})")

    @property
    def duration_minutes(self) -> int:
        """Total duration in whole minutes."""
        return int((self.end - self.start).total_seconds() // 60)

    @property
    def duration_seconds(self) -> int:
        return int((self.end - self.start).total_seconds())

    def overlaps(self, other: TimeRange) -> bool:
        return self.start < other.end and self.end > other.start

    def spans_days(self) -> int:
        """Number of calendar days this range spans (1 = same day)."""
        return (self.end.date() - self.start.date()).days + 1
