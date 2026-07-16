"""Domain Service: FeeCalculator.

Business rules:
- Thời gian <= free_minutes  → fee = 0
- Tính phí theo block (ceiling division)
- Nếu có phụ thu đêm và ca trải qua đêm → cộng thêm night_surcharge
- Nếu có day_max → giới hạn phí không vượt quá mức tối đa mỗi ngày
- Thuê bao còn hiệu lực → trả về Money(0) (kiểm tra trước khi gọi hàm này)
"""

from __future__ import annotations

from datetime import datetime, time

from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.value_objects.money import Money


class FeeCalculator:
    """Pure domain service — no I/O, no side effects."""

    def calculate(
        self,
        entry: datetime,
        exit_: datetime,
        rule: FeeRule,
    ) -> Money:
        """Calculate parking fee for a session.

        Args:
            entry:  Entry datetime (timezone-naive, local time).
            exit_:  Exit datetime (must be >= entry).
            rule:   Active FeeRule for the vehicle type.

        Returns:
            Money (int VND) — fee for the session.
        """
        total_minutes = int((exit_ - entry).total_seconds() // 60)
        billable_minutes = max(0, total_minutes - rule.free_minutes)

        if billable_minutes == 0:
            return Money.zero()

        # Ceiling division: number of billing blocks
        blocks = -(-billable_minutes // rule.block_minutes)  # math.ceil without import
        fee = Money(blocks * rule.price_per_block)

        # Night surcharge
        if rule.night_surcharge is not None and self._overlaps_night(entry, exit_, rule):
            # TODO(business-confirm): when session spans multiple nights, apply surcharge once
            # or once per night? Assumed: once per overlapping night for now.
            fee = fee + Money(rule.night_surcharge)

        # Day maximum — applied per calendar day.
        # For multi-day sessions we compute each day's cap separately and sum.
        # TODO(business-confirm): confirm multi-day capping strategy with business.
        if rule.day_max is not None:
            fee = self._apply_day_max(entry, exit_, fee, rule)

        return fee

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _overlaps_night(
        self,
        entry: datetime,
        exit_: datetime,
        rule: FeeRule,
    ) -> bool:
        """Return True if the session overlaps any night period.

        Night is defined as [night_start_hour, 24) ∪ [0, night_end_hour).
        """
        night_start = time(rule.night_start_hour, 0)
        night_end = time(rule.night_end_hour, 0)

        # Iterate each day between entry and exit
        current = entry
        while current < exit_:
            t = current.time()
            if t >= night_start or t < night_end:
                return True
            # Advance by 1 hour to check next window
            from datetime import timedelta  # local import to keep module imports clean
            current = current + timedelta(hours=1)
        return False

    def _apply_day_max(
        self,
        entry: datetime,
        exit_: datetime,
        raw_fee: Money,
        rule: FeeRule,
    ) -> Money:
        """Cap fee using day_max per calendar day.

        Simple approach: for each calendar day spanned, compute proportional
        fee and cap to day_max, then sum across days.

        TODO(business-confirm): confirm whether multi-day sessions use per-day
        cap or total session cap.
        """
        assert rule.day_max is not None  # guaranteed by caller
        day_max = Money(rule.day_max)

        # If the session fits within 1 calendar day — simple cap
        if entry.date() == exit_.date():
            return raw_fee.min(day_max)

        # Multi-day: cap total fee to (number_of_days × day_max)
        num_days = (exit_.date() - entry.date()).days + 1
        total_max = Money(rule.day_max * num_days)
        return raw_fee.min(total_max)
