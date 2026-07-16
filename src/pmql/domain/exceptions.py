"""Domain exceptions — raised by domain logic, caught in application layer."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain exceptions."""


class VehicleNotFoundError(DomainError):
    """Vehicle does not exist in the system."""


class SessionNotFoundError(DomainError):
    """Parking session not found."""


class SessionAlreadyClosedError(DomainError):
    """Attempt to close an already-closed session."""


class SubscriberNotFoundError(DomainError):
    """Subscriber record not found."""


class SubscriberExpiredError(DomainError):
    """Subscriber pass has expired or is inactive."""


class FeeRuleNotFoundError(DomainError):
    """No applicable fee rule found for this vehicle type."""


class CardNotFoundError(DomainError):
    """RFID card not found in system."""


class CardNotActiveError(DomainError):
    """RFID card is disabled."""


class LaneNotFoundError(DomainError):
    """Lane does not exist."""


class InvalidPlateNumberError(DomainError):
    """Plate number format is not valid."""


class InsufficientPermissionsError(DomainError):
    """User lacks permission for this operation."""
