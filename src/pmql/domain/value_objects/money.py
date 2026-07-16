"""Value Object: Money — integer-only, unit = VND (đồng)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    amount: int

    def __post_init__(self) -> None:
        if not isinstance(self.amount, int):
            raise TypeError(f"Money.amount must be int (VND), got {type(self.amount).__name__}.")
        if self.amount < 0:
            raise ValueError(f"Money amount cannot be negative, got {self.amount}")

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Money subtraction result cannot be negative")
        return Money(result)

    def __lt__(self, other: Money) -> bool:
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        return self.amount >= other.amount

    def min(self, other: Money) -> Money:
        return self if self.amount <= other.amount else other

    def max(self, other: Money) -> Money:
        return self if self.amount >= other.amount else other

    def __repr__(self) -> str:
        return f"Money({self.amount:,} VND)"

    @classmethod
    def zero(cls) -> Money:
        return cls(0)
