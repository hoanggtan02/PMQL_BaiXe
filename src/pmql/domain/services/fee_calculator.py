"""Domain Service: FeeCalculator."""

from __future__ import annotations

from datetime import datetime, time

from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.value_objects.money import Money


class FeeCalculator:
    def calculate(self, entry: datetime, exit_: datetime, rule: FeeRule) -> Money:
        total_minutes = int((exit_ - entry).total_seconds() // 60)
        billable_minutes = max(0, total_minutes - rule.free_minutes)

        if billable_minutes == 0:
            return Money.zero()

        blocks = -(-billable_minutes // rule.block_minutes)
        fee = Money(blocks * rule.price_per_block)

        if rule.night_surcharge is not None and self._overlaps_night(entry, exit_, rule):
            fee = fee + Money(rule.night_surcharge)

        if rule.day_max is not None:
            fee = self._apply_day_max(entry, exit_, fee, rule)

        return fee

    def _overlaps_night(self, entry: datetime, exit_: datetime, rule: FeeRule) -> bool:
        night_start = time(rule.night_start_hour, 0)
        night_end = time(rule.night_end_hour, 0)
        current = entry
        while current < exit_:
            t = current.time()
            if t >= night_start or t < night_end:
                return True
            from datetime import timedelta
            current = current + timedelta(hours=1)
        return False

    def _apply_day_max(self, entry: datetime, exit_: datetime, raw_fee: Money, rule: FeeRule) -> Money:
        assert rule.day_max is not None
        day_max = Money(rule.day_max)
        if entry.date() == exit_.date():
            return raw_fee.min(day_max)
        num_days = (exit_.date() - entry.date()).days + 1
        total_max = Money(rule.day_max * num_days)
        return raw_fee.min(total_max)
