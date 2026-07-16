"""Unit tests for FeeCalculator — pure domain logic, no I/O."""

from __future__ import annotations

from datetime import datetime

from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.services.fee_calculator import FeeCalculator


def make_rule(**overrides: object) -> FeeRule:
    defaults = dict(
        vehicle_type="motorbike",
        free_minutes=10,
        block_minutes=60,
        price_per_block=5000,
    )
    defaults.update(overrides)
    return FeeRule(**defaults)  # type: ignore[arg-type]


def test_within_free_minutes_is_zero() -> None:
    calc = FeeCalculator()
    rule = make_rule(free_minutes=15)
    entry = datetime(2026, 1, 1, 8, 0)
    exit_ = datetime(2026, 1, 1, 8, 10)

    fee = calc.calculate(entry, exit_, rule)

    assert fee.amount == 0


def test_charges_one_block_after_free_period() -> None:
    calc = FeeCalculator()
    rule = make_rule(free_minutes=10, block_minutes=60, price_per_block=5000)
    entry = datetime(2026, 1, 1, 8, 0)
    exit_ = datetime(2026, 1, 1, 8, 30)  # 30 min total, 20 min billable -> 1 block

    fee = calc.calculate(entry, exit_, rule)

    assert fee.amount == 5000


def test_ceiling_division_rounds_up_to_next_block() -> None:
    calc = FeeCalculator()
    rule = make_rule(free_minutes=0, block_minutes=60, price_per_block=5000)
    entry = datetime(2026, 1, 1, 8, 0)
    exit_ = datetime(2026, 1, 1, 9, 1)  # 61 min -> 2 blocks

    fee = calc.calculate(entry, exit_, rule)

    assert fee.amount == 10000


def test_day_max_caps_fee_within_same_day() -> None:
    calc = FeeCalculator()
    rule = make_rule(free_minutes=0, block_minutes=60, price_per_block=20000, day_max=100000)
    entry = datetime(2026, 1, 1, 6, 0)
    exit_ = datetime(2026, 1, 1, 18, 0)  # 12 blocks * 20,000 = 240,000, capped to 100,000

    fee = calc.calculate(entry, exit_, rule)

    assert fee.amount == 100000


def test_subscriber_zero_fee_is_the_caller_responsibility() -> None:
    # FeeCalculator itself has no concept of subscribers — that check happens
    # in the use case *before* calling calculate(). This test documents that
    # contract so it doesn't silently drift.
    calc = FeeCalculator()
    rule = make_rule(free_minutes=0, price_per_block=5000)
    entry = datetime(2026, 1, 1, 8, 0)
    exit_ = datetime(2026, 1, 1, 9, 0)

    fee = calc.calculate(entry, exit_, rule)

    assert fee.amount > 0  # calculator always charges; use case must short-circuit for subscribers
