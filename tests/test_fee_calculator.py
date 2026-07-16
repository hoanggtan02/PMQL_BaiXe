from __future__ import annotations
from datetime import datetime
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.services.fee_calculator import FeeCalculator


def make_rule(**overrides):
    defaults = dict(vehicle_type="motorbike", free_minutes=10, block_minutes=60, price_per_block=5000)
    defaults.update(overrides)
    return FeeRule(**defaults)


def test_within_free_minutes_is_zero():
    calc = FeeCalculator()
    rule = make_rule(free_minutes=15)
    fee = calc.calculate(datetime(2026,1,1,8,0), datetime(2026,1,1,8,10), rule)
    assert fee.amount == 0


def test_charges_one_block_after_free_period():
    calc = FeeCalculator()
    rule = make_rule(free_minutes=10, block_minutes=60, price_per_block=5000)
    fee = calc.calculate(datetime(2026,1,1,8,0), datetime(2026,1,1,8,30), rule)
    assert fee.amount == 5000
