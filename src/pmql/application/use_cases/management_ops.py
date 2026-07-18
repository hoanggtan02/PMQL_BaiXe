"""CRUD use cases for the management screens and CLI.

They deliberately use the existing repository ports, keeping storage and UI
details outside the application layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from pmql.application.ports.repositories import IFeeRuleRepository, ISubscriberRepository, IUserRepository, IShiftRepository, IVehicleRepository
from pmql.application.ports.security_port import IPasswordHasher
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.vehicle import Vehicle
from pmql.domain.exceptions import FeeRuleNotFoundError, InvalidFeeRuleError, InvalidRoleError, SubscriberNotFoundError, UserNotFoundError, ShiftNotFoundError
from pmql.domain.entities.shift import Shift


@dataclass
class SubscriberUpdateInput:
    subscriber_id: str
    full_name: str
    phone: str
    identity_card: str
    vehicles: list[dict[str, str]]
    valid_from: date
    valid_until: date
    email: str | None = None
    is_active: bool = True


class SubscriberManagementUseCase:
    def __init__(self, repo: ISubscriberRepository, vehicle_repo: IVehicleRepository) -> None:
        self._repo = repo
        self._vehicles = vehicle_repo

    async def update(self, inp: SubscriberUpdateInput) -> None:
        subscriber = await self._repo.get_by_id(inp.subscriber_id)
        if subscriber is None:
            raise SubscriberNotFoundError(inp.subscriber_id)
        subscriber.full_name, subscriber.phone = inp.full_name, inp.phone
        subscriber.identity_card = inp.identity_card
        subscriber.valid_from, subscriber.valid_until = inp.valid_from, inp.valid_until
        subscriber.email, subscriber.is_active = inp.email, inp.is_active
        subscriber.updated_at, subscriber.sync_version = datetime.utcnow(), subscriber.sync_version + 1
        await self._repo.update(subscriber)

        # Sync vehicles: remove old, add new
        existing_vehicles = await self._vehicles.list_by_subscriber(inp.subscriber_id)
        for v in existing_vehicles:
            await self._vehicles.delete(v.id)

        for v_data in inp.vehicles:
            vehicle = Vehicle(
                branch_id=subscriber.branch_id,
                plate_number=v_data["plate_number"],
                vehicle_type=v_data["vehicle_type"],
                subscriber_id=subscriber.id
            )
            await self._vehicles.create(vehicle)

    async def delete(self, subscriber_id: str) -> None:
        if await self._repo.get_by_id(subscriber_id) is None:
            raise SubscriberNotFoundError(subscriber_id)
        await self._repo.delete(subscriber_id)


@dataclass
class FeeRuleInput:
    branch_id: str
    name: str
    vehicle_type: str
    free_minutes: int
    block_minutes: int
    price_per_block: int
    day_max: int | None = None
    is_active: bool = True


class FeeRuleManagementUseCase:
    def __init__(self, repo: IFeeRuleRepository) -> None:
        self._repo = repo

    async def create(self, inp: FeeRuleInput) -> str:
        if inp.block_minutes <= 0 or inp.price_per_block < 0 or inp.free_minutes < 0:
            raise InvalidFeeRuleError("Invalid fee rule amounts")
        rule = FeeRule(**inp.__dict__)
        await self._repo.create(rule)
        return rule.id

    async def update(self, rule_id: str, inp: FeeRuleInput) -> None:
        rule = await self._repo.get_by_id(rule_id)
        if rule is None:
            raise FeeRuleNotFoundError(rule_id)
        if inp.block_minutes <= 0 or inp.price_per_block < 0 or inp.free_minutes < 0:
            raise InvalidFeeRuleError("Invalid fee rule amounts")
        for field, value in inp.__dict__.items():
            if field != "branch_id":
                setattr(rule, field, value)
        rule.updated_at, rule.sync_version = datetime.utcnow(), rule.sync_version + 1
        await self._repo.update(rule)

    async def delete(self, rule_id: str) -> None:
        if await self._repo.get_by_id(rule_id) is None:
            raise FeeRuleNotFoundError(rule_id)
        await self._repo.delete(rule_id)


@dataclass
class UserUpdateInput:
    user_id: str
    full_name: str
    role: str
    is_active: bool
    password: str | None = None


class UserManagementUseCase:
    def __init__(self, repo: IUserRepository, hasher: IPasswordHasher) -> None:
        self._repo, self._hasher = repo, hasher

    async def update(self, inp: UserUpdateInput) -> None:
        user = await self._repo.get_by_id(inp.user_id)
        if user is None:
            raise UserNotFoundError(inp.user_id)
        if not inp.role.strip():
            raise InvalidRoleError(inp.role)
        user.full_name, user.role, user.is_active = inp.full_name, inp.role, inp.is_active
        if inp.password:
            user.password_hash = self._hasher.hash(inp.password)
        user.updated_at, user.sync_version = datetime.utcnow(), user.sync_version + 1
        await self._repo.update(user)

    async def delete(self, user_id: str) -> None:
        if await self._repo.get_by_id(user_id) is None:
            raise UserNotFoundError(user_id)
        await self._repo.delete(user_id)


@dataclass
class ShiftInput:
    branch_id: str
    operator_id: str
    start_time: datetime
    end_time: datetime | None = None
    total_sessions: int = 0
    total_revenue: int = 0
    status: str = "OPEN"


class ShiftManagementUseCase:
    def __init__(self, repo: IShiftRepository) -> None:
        self._repo = repo

    async def create(self, inp: ShiftInput) -> str:
        shift = Shift(**inp.__dict__)
        await self._repo.create(shift)
        return shift.id

    async def update(self, shift_id: str, inp: ShiftInput) -> None:
        shift = await self._repo.get_by_id(shift_id)
        if shift is None:
            raise ShiftNotFoundError(shift_id)
        for field, value in inp.__dict__.items():
            if field != "branch_id":
                setattr(shift, field, value)
        shift.updated_at, shift.sync_version = datetime.utcnow(), shift.sync_version + 1
        await self._repo.update(shift)

    async def delete(self, shift_id: str) -> None:
        if await self._repo.get_by_id(shift_id) is None:
            raise ShiftNotFoundError(shift_id)
        await self._repo.delete(shift_id)
