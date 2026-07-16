"""Value objects package."""
from pmql.domain.value_objects.money import Money
from pmql.domain.value_objects.plate_number import PlateNumber
from pmql.domain.value_objects.time_range import TimeRange
__all__ = ["Money", "PlateNumber", "TimeRange"]
