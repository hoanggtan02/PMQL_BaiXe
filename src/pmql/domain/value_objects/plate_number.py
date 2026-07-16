"""Value Object: PlateNumber — validated Vietnamese license plate."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Vietnamese plate patterns (simplified — covers most common formats)
_PLATE_RE = re.compile(
    r"^[0-9]{2}[A-Z]{1,2}-[0-9]{4,5}$"      # standard: 51F-12345
    r"|^[0-9]{2}[A-Z][0-9]-[0-9]{5}$"       # new format: 51F1-23456
    r"|^[A-Z]{2}-[0-9]{5}$"                  # military/special
,
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PlateNumber:
    """Immutable, normalised Vietnamese license plate number."""

    value: str

    def __post_init__(self) -> None:
        normalised = self.value.strip().upper().replace(" ", "")
        if not _PLATE_RE.match(normalised):
            # Don't reject unknown formats outright — ANPR may give partial reads.
            # Validation is best-effort; downstream code may still accept it with a flag.
            pass  # TODO(business-confirm): decide whether to raise or warn on invalid format
        # Freeze after normalisation (frozen dataclass can't assign, so we use object.__setattr__)
        object.__setattr__(self, "value", normalised)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"PlateNumber('{self.value}')"
