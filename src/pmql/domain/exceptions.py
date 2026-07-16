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


class VehicleAlreadyInsideError(DomainError):
    """Vehicle already has an ACTIVE session — cannot record a second entry."""


class InvalidPlateNumberError(DomainError):
    """Plate number format is not valid."""


class InsufficientPermissionsError(DomainError):
    """User lacks permission for this operation."""


# ── Added: shift / auth / alert use cases ──────────────────────────────────


class ShiftAlreadyOpenError(DomainError):
    """Operator already has an OPEN shift — must close it before opening another."""


class ShiftNotFoundError(DomainError):
    """No open shift found for this operator."""


class InvalidCredentialsError(DomainError):
    """Username/password combination is invalid, or the user is inactive."""


class UsernameAlreadyExistsError(DomainError):
    """Username is already taken."""


class InvalidRoleError(DomainError):
    """The supplied role is not one of the supported system roles."""


class AlertNotFoundError(DomainError):
    """Alert does not exist or is not currently unacknowledged."""
