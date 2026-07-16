"""Value Object: PlateNumber."""
from __future__ import annotations
import re
from dataclasses import dataclass

_PLATE_RE = re.compile(
    r"^[0-9]{2}[A-Z]{1,2}-[0-9]{4,5}$"
    r"|^[0-9]{2}[A-Z][0-9]-[0-9]{5}$"
    r"|^[A-Z]{2}-[0-9]{5}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PlateNumber:
    value: str

    def __post_init__(self) -> None:
        normalised = self.value.strip().upper().replace(" ", "")
        object.__setattr__(self, "value", normalised)

    def __str__(self) -> str:
        return self.value
