"""Application Ports: Repository interfaces.

All repository interfaces live here. Infrastructure layer provides
concrete implementations. Use cases depend ONLY on these interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pmql.domain.entities.alert import Alert
    from pmql.domain.entities.card import Card
    from pmql.domain.entities.device import Device
    from pmql.domain.entities.fee_rule import FeeRule
    from pmql.domain.entities.lane import Lane
    from pmql.domain.entities.session import ParkingSession
    from pmql.domain.entities.shift import Shift
    from pmql.domain.entities.subscriber import Subscriber
    from pmql.domain.entities.user import User
    from pmql.domain.entities.vehicle import Vehicle


class ISessionRepository(ABC):
    """CRUD for ParkingSession."""

    @abstractmethod
    async def create(self, session: ParkingSession) -> None: ...

    @abstractmethod
    async def get_by_id(self, session_id: str) -> ParkingSession | None: ...

    @abstractmethod
    async def get_active_by_plate(self, plate_number: str) -> ParkingSession | None: ...

    @abstractmethod
    async def get_active_by_rfid(self, rfid_code: str) -> ParkingSession | None: ...

    @abstractmethod
    async def update(self, session: ParkingSession) -> None: ...

    @abstractmethod
    async def list_by_shift(self, shift_id: str) -> list[ParkingSession]: ...

    @abstractmethod
    async def list_recent(self, branch_id: str, limit: int = 50) -> list[ParkingSession]:
        """List the most recent sessions for a branch (newest entry first).

        Added to back the `list-sessions` CLI command mentioned in the
        README but never registered in `build_parser()` — the use case
        layer previously had no way to list sessions at all.
        """
        ...


class IVehicleRepository(ABC):
    @abstractmethod
    async def create(self, vehicle: Vehicle) -> None: ...

    @abstractmethod
    async def get_by_id(self, vehicle_id: str) -> Vehicle | None: ...

    @abstractmethod
    async def get_by_plate(self, plate_number: str) -> Vehicle | None: ...

    @abstractmethod
    async def get_by_rfid(self, rfid_tag: str) -> Vehicle | None: ...

    @abstractmethod
    async def update(self, vehicle: Vehicle) -> None: ...


class ISubscriberRepository(ABC):
    @abstractmethod
    async def get_by_id(self, subscriber_id: str) -> Subscriber | None: ...

    @abstractmethod
    async def get_by_vehicle_type(
        self, vehicle_type: str, is_active: bool = True
    ) -> list[Subscriber]: ...

    @abstractmethod
    async def create(self, subscriber: Subscriber) -> None: ...

    @abstractmethod
    async def update(self, subscriber: Subscriber) -> None: ...

    @abstractmethod
    async def delete(self, subscriber_id: str) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[Subscriber]: ...


class ICardRepository(ABC):
    @abstractmethod
    async def get_by_rfid_code(self, rfid_code: str) -> Card | None: ...

    @abstractmethod
    async def get_by_id(self, card_id: str) -> Card | None: ...

    @abstractmethod
    async def create(self, card: Card) -> None: ...

    @abstractmethod
    async def update(self, card: Card) -> None: ...

    @abstractmethod
    async def list_by_subscriber(self, subscriber_id: str) -> list[Card]: ...

    @abstractmethod
    async def list_all(self) -> list[Card]: ...

    @abstractmethod
    async def delete(self, card_id: str) -> None: ...


class IFeeRuleRepository(ABC):
    @abstractmethod
    async def get_active_by_vehicle_type(self, vehicle_type: str) -> FeeRule | None: ...

    @abstractmethod
    async def get_by_id(self, rule_id: str) -> FeeRule | None: ...

    @abstractmethod
    async def create(self, rule: FeeRule) -> None: ...

    @abstractmethod
    async def update(self, rule: FeeRule) -> None: ...

    @abstractmethod
    async def delete(self, rule_id: str) -> None:
        """Remove a fee rule permanently.

        Was missing (see README "Chưa có") even though the rest of the
        CRUD surface existed — callers previously had no way to retire a
        rule other than setting `is_active=False` via `update()`.
        """
        ...

    @abstractmethod
    async def list_all(self) -> list[FeeRule]: ...


class ILaneRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lane_id: str) -> Lane | None: ...

    @abstractmethod
    async def list_active(self) -> list[Lane]: ...

    @abstractmethod
    async def create(self, lane: Lane) -> None: ...

    @abstractmethod
    async def update(self, lane: Lane) -> None: ...

    @abstractmethod
    async def delete(self, lane_id: str) -> None: ...


class IShiftRepository(ABC):
    @abstractmethod
    async def create(self, shift: Shift) -> None: ...

    @abstractmethod
    async def get_by_id(self, shift_id: str) -> Shift | None: ...

    @abstractmethod
    async def get_open_by_operator(self, operator_id: str) -> Shift | None: ...

    @abstractmethod
    async def update(self, shift: Shift) -> None: ...

    @abstractmethod
    async def delete(self, shift_id: str) -> None: ...

    @abstractmethod
    async def list_by_branch(self, branch_id: str, limit: int = 50) -> list[Shift]: ...


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...

    @abstractmethod
    async def delete(self, user_id: str) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...


class IAlertRepository(ABC):
    @abstractmethod
    async def create(self, alert: Alert) -> None: ...

    @abstractmethod
    async def get_by_id(self, alert_id: str) -> Alert | None: ...

    @abstractmethod
    async def update(self, alert: Alert) -> None: ...

    @abstractmethod
    async def list_unacknowledged(self) -> list[Alert]: ...

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[Alert]: ...


class IDeviceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, device_id: str) -> Device | None: ...

    @abstractmethod
    async def update_status(self, device_id: str, is_online: bool) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[Device]: ...
