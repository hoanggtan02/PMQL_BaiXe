"""Concrete repository implementations backed by the local SQLite database.

Each class implements the corresponding interface from
`pmql.application.ports.repositories`. All of them share one
`AsyncSession` instance so a use case's writes are part of a single
transaction (see `Database.session()`).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from pmql.infrastructure.persistence.sqlite.models import (
    AlertModel,
    CardModel,
    DeviceModel,
    FeeRuleModel,
    LaneModel,
    ParkingSessionModel,
    ShiftModel,
    SubscriberModel,
    UserModel,
    VehicleModel,
)

# ──────────────────────────────────────────────────────────────────────────
# Mappers: ORM row <-> domain entity
# ──────────────────────────────────────────────────────────────────────────


def _lane_to_entity(row: LaneModel) -> Lane:
    return Lane(
        id=row.id,
        branch_id=row.branch_id,
        name=row.name,
        direction=row.direction,
        camera_source=row.camera_source,
        rfid_device_id=row.rfid_device_id,
        barrier_device_id=row.barrier_device_id,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _vehicle_to_entity(row: VehicleModel) -> Vehicle:
    return Vehicle(
        id=row.id,
        branch_id=row.branch_id,
        plate_number=row.plate_number,
        vehicle_type=row.vehicle_type,
        rfid_tag=row.rfid_tag,
        subscriber_id=row.subscriber_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _card_to_entity(row: CardModel) -> Card:
    return Card(
        id=row.id,
        branch_id=row.branch_id,
        rfid_code=row.rfid_code,
        subscriber_id=row.subscriber_id,
        vehicle_id=row.vehicle_id,
        is_active=row.is_active,
        issued_at=row.issued_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _subscriber_to_entity(row: SubscriberModel) -> Subscriber:
    return Subscriber(
        id=row.id,
        branch_id=row.branch_id,
        full_name=row.full_name,
        phone=row.phone,
        email=row.email,
        vehicle_type=row.vehicle_type,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _fee_rule_to_entity(row: FeeRuleModel) -> FeeRule:
    return FeeRule(
        id=row.id,
        branch_id=row.branch_id,
        name=row.name,
        vehicle_type=row.vehicle_type,
        free_minutes=row.free_minutes,
        block_minutes=row.block_minutes,
        price_per_block=row.price_per_block,
        day_max=row.day_max,
        night_surcharge=row.night_surcharge,
        night_start_hour=row.night_start_hour,
        night_end_hour=row.night_end_hour,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _session_to_entity(row: ParkingSessionModel) -> ParkingSession:
    return ParkingSession(
        id=row.id,
        branch_id=row.branch_id,
        lane_in_id=row.lane_in_id,
        lane_out_id=row.lane_out_id,
        vehicle_id=row.vehicle_id,
        plate_number=row.plate_number,
        rfid_card_id=row.rfid_card_id,
        subscriber_id=row.subscriber_id,
        shift_id=row.shift_id,
        entry_time=row.entry_time,
        exit_time=row.exit_time,
        fee_rule_id=row.fee_rule_id,
        fee_amount=row.fee_amount,
        status=row.status,
        entry_plate_image_path=row.entry_plate_image_path,
        exit_plate_image_path=row.exit_plate_image_path,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _user_to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        branch_id=row.branch_id,
        username=row.username,
        password_hash=row.password_hash,
        full_name=row.full_name,
        role=row.role,
        is_active=row.is_active,
        last_login_at=row.last_login_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _shift_to_entity(row: ShiftModel) -> Shift:
    return Shift(
        id=row.id,
        branch_id=row.branch_id,
        operator_id=row.operator_id,
        start_time=row.start_time,
        end_time=row.end_time,
        total_sessions=row.total_sessions,
        total_revenue=row.total_revenue,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _alert_to_entity(row: AlertModel) -> Alert:
    return Alert(
        id=row.id,
        branch_id=row.branch_id,
        alert_type=row.alert_type,
        severity=row.severity,
        message=row.message,
        related_entity_id=row.related_entity_id,
        is_acknowledged=row.is_acknowledged,
        acknowledged_by=row.acknowledged_by,
        acknowledged_at=row.acknowledged_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


def _device_to_entity(row: DeviceModel) -> Device:
    return Device(
        id=row.id,
        branch_id=row.branch_id,
        name=row.name,
        device_type=row.device_type,
        connection_string=row.connection_string,
        is_online=row.is_online,
        last_seen_at=row.last_seen_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        sync_version=row.sync_version,
    )


# ──────────────────────────────────────────────────────────────────────────
# Repositories
# ──────────────────────────────────────────────────────────────────────────


class SQLiteLaneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lane_id: str) -> Lane | None:
        row = await self._session.get(LaneModel, lane_id)
        return _lane_to_entity(row) if row and not row.is_deleted else None

    async def list_active(self) -> list[Lane]:
        result = await self._session.execute(select(LaneModel).where(LaneModel.is_active.is_(True), LaneModel.is_deleted.is_(False)))
        return [_lane_to_entity(r) for r in result.scalars().all()]

    async def create(self, lane: Lane) -> None:
        self._session.add(
            LaneModel(
                id=lane.id,
                branch_id=lane.branch_id,
                name=lane.name,
                direction=lane.direction,
                camera_source=lane.camera_source,
                rfid_device_id=lane.rfid_device_id,
                barrier_device_id=lane.barrier_device_id,
                is_active=lane.is_active,
                created_at=lane.created_at,
                updated_at=lane.updated_at,
                sync_version=lane.sync_version,
            )
        )
        await self._session.flush()

    async def update(self, lane: Lane) -> None:
        row = await self._session.get(LaneModel, lane.id)
        if row is None:
            raise ValueError(f"Lane {lane.id} not found")
        row.name = lane.name
        row.direction = lane.direction
        row.camera_source = lane.camera_source
        row.rfid_device_id = lane.rfid_device_id
        row.barrier_device_id = lane.barrier_device_id
        row.is_active = lane.is_active
        row.updated_at = lane.updated_at
        row.sync_version = lane.sync_version
        await self._session.flush()

    async def delete(self, lane_id: str) -> None:
        row = await self._session.get(LaneModel, lane_id)
        if row is not None and not row.is_deleted:
            row.is_deleted = True
            await self._session.flush()


class SQLiteVehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, vehicle: Vehicle) -> None:
        self._session.add(
            VehicleModel(
                id=vehicle.id,
                branch_id=vehicle.branch_id,
                plate_number=vehicle.plate_number,
                vehicle_type=vehicle.vehicle_type,
                rfid_tag=vehicle.rfid_tag,
                subscriber_id=vehicle.subscriber_id,
                created_at=vehicle.created_at,
                updated_at=vehicle.updated_at,
                sync_version=vehicle.sync_version,
            )
        )
        await self._session.flush()

    async def get_by_id(self, vehicle_id: str) -> Vehicle | None:
        row = await self._session.get(VehicleModel, vehicle_id)
        return _vehicle_to_entity(row) if row else None

    async def get_by_plate(self, plate_number: str) -> Vehicle | None:
        result = await self._session.execute(
            select(VehicleModel).where(VehicleModel.plate_number == plate_number)
        )
        row = result.scalars().first()
        return _vehicle_to_entity(row) if row else None

    async def get_by_rfid(self, rfid_tag: str) -> Vehicle | None:
        result = await self._session.execute(select(VehicleModel).where(VehicleModel.rfid_tag == rfid_tag))
        row = result.scalars().first()
        return _vehicle_to_entity(row) if row else None

    async def update(self, vehicle: Vehicle) -> None:
        row = await self._session.get(VehicleModel, vehicle.id)
        if row is None:
            raise ValueError(f"Vehicle {vehicle.id} not found")
        row.vehicle_type = vehicle.vehicle_type
        row.rfid_tag = vehicle.rfid_tag
        row.subscriber_id = vehicle.subscriber_id
        row.updated_at = vehicle.updated_at
        row.sync_version = vehicle.sync_version
        await self._session.flush()


class SQLiteCardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_rfid_code(self, rfid_code: str) -> Card | None:
        result = await self._session.execute(select(CardModel).where(CardModel.rfid_code == rfid_code, CardModel.is_deleted.is_(False)))
        row = result.scalars().first()
        return _card_to_entity(row) if row else None

    async def get_by_id(self, card_id: str) -> Card | None:
        row = await self._session.get(CardModel, card_id)
        return _card_to_entity(row) if row and not row.is_deleted else None

    async def create(self, card: Card) -> None:
        self._session.add(
            CardModel(
                id=card.id,
                branch_id=card.branch_id,
                rfid_code=card.rfid_code,
                subscriber_id=card.subscriber_id,
                vehicle_id=card.vehicle_id,
                is_active=card.is_active,
                issued_at=card.issued_at,
                created_at=card.created_at,
                updated_at=card.updated_at,
                sync_version=card.sync_version,
            )
        )
        await self._session.flush()

    async def update(self, card: Card) -> None:
        row = await self._session.get(CardModel, card.id)
        if row is None:
            raise ValueError(f"Card {card.id} not found")
        row.subscriber_id = card.subscriber_id
        row.vehicle_id = card.vehicle_id
        row.is_active = card.is_active
        row.updated_at = card.updated_at
        row.sync_version = card.sync_version
        await self._session.flush()

    async def list_by_subscriber(self, subscriber_id: str) -> list[Card]:
        result = await self._session.execute(select(CardModel).where(CardModel.subscriber_id == subscriber_id, CardModel.is_deleted.is_(False)))
        return [_card_to_entity(r) for r in result.scalars().all()]

    async def list_all(self) -> list[Card]:
        result = await self._session.execute(select(CardModel).where(CardModel.is_deleted.is_(False)).order_by(CardModel.created_at.desc()))
        return [_card_to_entity(r) for r in result.scalars().all()]

    async def delete(self, card_id: str) -> None:
        row = await self._session.get(CardModel, card_id)
        if row is not None and not row.is_deleted:
            row.is_deleted = True
            await self._session.flush()


class SQLiteSubscriberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, subscriber_id: str) -> Subscriber | None:
        row = await self._session.get(SubscriberModel, subscriber_id)
        return _subscriber_to_entity(row) if row and not row.is_deleted else None

    async def get_by_vehicle_type(self, vehicle_type: str, is_active: bool = True) -> list[Subscriber]:
        result = await self._session.execute(
            select(SubscriberModel).where(
                SubscriberModel.vehicle_type == vehicle_type,
                SubscriberModel.is_active.is_(is_active),
                SubscriberModel.is_deleted.is_(False),
            )
        )
        return [_subscriber_to_entity(r) for r in result.scalars().all()]

    async def create(self, subscriber: Subscriber) -> None:
        self._session.add(
            SubscriberModel(
                id=subscriber.id,
                branch_id=subscriber.branch_id,
                full_name=subscriber.full_name,
                phone=subscriber.phone,
                email=subscriber.email,
                vehicle_type=subscriber.vehicle_type,
                valid_from=subscriber.valid_from,
                valid_until=subscriber.valid_until,
                is_active=subscriber.is_active,
                created_at=subscriber.created_at,
                updated_at=subscriber.updated_at,
                sync_version=subscriber.sync_version,
            )
        )
        await self._session.flush()

    async def update(self, subscriber: Subscriber) -> None:
        row = await self._session.get(SubscriberModel, subscriber.id)
        if row is None:
            raise ValueError(f"Subscriber {subscriber.id} not found")
        row.full_name = subscriber.full_name
        row.phone = subscriber.phone
        row.email = subscriber.email
        row.vehicle_type = subscriber.vehicle_type
        row.valid_from = subscriber.valid_from
        row.valid_until = subscriber.valid_until
        row.is_active = subscriber.is_active
        row.updated_at = subscriber.updated_at
        row.sync_version = subscriber.sync_version
        await self._session.flush()

    async def delete(self, subscriber_id: str) -> None:
        row = await self._session.get(SubscriberModel, subscriber_id)
        if row is not None and not row.is_deleted:
            row.is_deleted = True
            await self._session.flush()

    async def list_all(self) -> list[Subscriber]:
        result = await self._session.execute(select(SubscriberModel).where(SubscriberModel.is_deleted.is_(False)))
        return [_subscriber_to_entity(r) for r in result.scalars().all()]


class SQLiteFeeRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_vehicle_type(self, vehicle_type: str) -> FeeRule | None:
        result = await self._session.execute(
            select(FeeRuleModel).where(
                FeeRuleModel.vehicle_type == vehicle_type,
                FeeRuleModel.is_active.is_(True),
                FeeRuleModel.is_deleted.is_(False),
            )
        )
        row = result.scalars().first()
        return _fee_rule_to_entity(row) if row else None

    async def get_by_id(self, rule_id: str) -> FeeRule | None:
        row = await self._session.get(FeeRuleModel, rule_id)
        return _fee_rule_to_entity(row) if row and not row.is_deleted else None

    async def create(self, rule: FeeRule) -> None:
        self._session.add(
            FeeRuleModel(
                id=rule.id,
                branch_id=rule.branch_id,
                name=rule.name,
                vehicle_type=rule.vehicle_type,
                free_minutes=rule.free_minutes,
                block_minutes=rule.block_minutes,
                price_per_block=rule.price_per_block,
                day_max=rule.day_max,
                night_surcharge=rule.night_surcharge,
                night_start_hour=rule.night_start_hour,
                night_end_hour=rule.night_end_hour,
                is_active=rule.is_active,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
                sync_version=rule.sync_version,
            )
        )
        await self._session.flush()

    async def update(self, rule: FeeRule) -> None:
        row = await self._session.get(FeeRuleModel, rule.id)
        if row is None:
            raise ValueError(f"FeeRule {rule.id} not found")
        row.name = rule.name
        row.free_minutes = rule.free_minutes
        row.block_minutes = rule.block_minutes
        row.price_per_block = rule.price_per_block
        row.day_max = rule.day_max
        row.night_surcharge = rule.night_surcharge
        row.night_start_hour = rule.night_start_hour
        row.night_end_hour = rule.night_end_hour
        row.is_active = rule.is_active
        row.updated_at = rule.updated_at
        row.sync_version = rule.sync_version
        await self._session.flush()

    async def delete(self, rule_id: str) -> None:
        # Added: IFeeRuleRepository previously had no delete() (see README
        # "Chưa có") — callers could only soft-disable via update(is_active
        # =False). This performs a real hard delete for retiring a rule.
        row = await self._session.get(FeeRuleModel, rule_id)
        if row is not None and not row.is_deleted:
            row.is_deleted = True
            await self._session.flush()

    async def list_all(self) -> list[FeeRule]:
        result = await self._session.execute(select(FeeRuleModel).where(FeeRuleModel.is_deleted.is_(False)))
        return [_fee_rule_to_entity(r) for r in result.scalars().all()]


class SQLiteSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, parking_session: ParkingSession) -> None:
        self._session.add(
            ParkingSessionModel(
                id=parking_session.id,
                branch_id=parking_session.branch_id,
                lane_in_id=parking_session.lane_in_id,
                lane_out_id=parking_session.lane_out_id,
                vehicle_id=parking_session.vehicle_id,
                plate_number=parking_session.plate_number,
                rfid_card_id=parking_session.rfid_card_id,
                subscriber_id=parking_session.subscriber_id,
                shift_id=parking_session.shift_id,
                entry_time=parking_session.entry_time,
                exit_time=parking_session.exit_time,
                fee_rule_id=parking_session.fee_rule_id,
                fee_amount=parking_session.fee_amount,
                status=parking_session.status,
                entry_plate_image_path=parking_session.entry_plate_image_path,
                exit_plate_image_path=parking_session.exit_plate_image_path,
                created_at=parking_session.created_at,
                updated_at=parking_session.updated_at,
                sync_version=parking_session.sync_version,
            )
        )
        await self._session.flush()

    async def get_by_id(self, session_id: str) -> ParkingSession | None:
        row = await self._session.get(ParkingSessionModel, session_id)
        return _session_to_entity(row) if row else None

    async def get_active_by_plate(self, plate_number: str) -> ParkingSession | None:
        result = await self._session.execute(
            select(ParkingSessionModel).where(
                ParkingSessionModel.plate_number == plate_number,
                ParkingSessionModel.status == "ACTIVE",
            )
        )
        row = result.scalars().first()
        return _session_to_entity(row) if row else None

    async def get_active_by_rfid(self, rfid_code: str) -> ParkingSession | None:
        result = await self._session.execute(
            select(ParkingSessionModel).where(
                ParkingSessionModel.rfid_card_id == rfid_code,
                ParkingSessionModel.status == "ACTIVE",
            )
        )
        row = result.scalars().first()
        return _session_to_entity(row) if row else None

    async def update(self, parking_session: ParkingSession) -> None:
        row = await self._session.get(ParkingSessionModel, parking_session.id)
        if row is None:
            raise ValueError(f"Session {parking_session.id} not found")
        row.lane_out_id = parking_session.lane_out_id
        row.vehicle_id = parking_session.vehicle_id
        row.exit_time = parking_session.exit_time
        row.fee_rule_id = parking_session.fee_rule_id
        row.fee_amount = parking_session.fee_amount
        row.status = parking_session.status
        row.exit_plate_image_path = parking_session.exit_plate_image_path
        row.updated_at = parking_session.updated_at
        row.sync_version = parking_session.sync_version
        await self._session.flush()

    async def list_by_shift(self, shift_id: str) -> list[ParkingSession]:
        # FIXED: sessions.shift_id now exists (see models.py) and is stamped
        # by VehicleEntryUseCase, so this filters correctly instead of
        # returning every session in the database regardless of shift.
        result = await self._session.execute(
            select(ParkingSessionModel).where(ParkingSessionModel.shift_id == shift_id)
        )
        return [_session_to_entity(r) for r in result.scalars().all()]

    async def list_recent(self, branch_id: str, limit: int = 50) -> list[ParkingSession]:
        # Added: backs the `list-sessions` CLI command referenced in the
        # README but never wired up — there was previously no way to list
        # sessions for a branch at all (only lookups by plate/rfid/shift).
        result = await self._session.execute(
            select(ParkingSessionModel)
            .where(ParkingSessionModel.branch_id == branch_id)
            .order_by(ParkingSessionModel.entry_time.desc())
            .limit(limit)
        )
        return [_session_to_entity(r) for r in result.scalars().all()]


class SQLiteUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.username == username, UserModel.is_deleted.is_(False)))
        row = result.scalars().first()
        return _user_to_entity(row) if row and not row.is_deleted else None

    async def get_by_id(self, user_id: str) -> User | None:
        row = await self._session.get(UserModel, user_id)
        return _user_to_entity(row) if row else None

    async def create(self, user: User) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                branch_id=user.branch_id,
                username=user.username,
                password_hash=user.password_hash,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
                sync_version=user.sync_version,
            )
        )
        await self._session.flush()

    async def update(self, user: User) -> None:
        row = await self._session.get(UserModel, user.id)
        if row is None:
            raise ValueError(f"User {user.id} not found")
        row.password_hash = user.password_hash
        row.full_name = user.full_name
        row.role = user.role
        row.is_active = user.is_active
        row.last_login_at = user.last_login_at
        row.updated_at = user.updated_at
        row.sync_version = user.sync_version
        await self._session.flush()

    async def delete(self, user_id: str) -> None:
        row = await self._session.get(UserModel, user_id)
        if row is not None and not row.is_deleted:
            row.is_deleted = True
            await self._session.flush()

    async def list_all(self) -> list[User]:
        result = await self._session.execute(select(UserModel).where(UserModel.is_deleted.is_(False)))
        return [_user_to_entity(r) for r in result.scalars().all()]


class SQLiteShiftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, shift: Shift) -> None:
        self._session.add(
            ShiftModel(
                id=shift.id,
                branch_id=shift.branch_id,
                operator_id=shift.operator_id,
                start_time=shift.start_time,
                end_time=shift.end_time,
                total_sessions=shift.total_sessions,
                total_revenue=shift.total_revenue,
                status=shift.status,
                created_at=shift.created_at,
                updated_at=shift.updated_at,
                sync_version=shift.sync_version,
            )
        )
        await self._session.flush()

    async def get_open_by_operator(self, operator_id: str) -> Shift | None:
        result = await self._session.execute(
            select(ShiftModel).where(ShiftModel.operator_id == operator_id, ShiftModel.status == "OPEN")
        )
        row = result.scalars().first()
        return _shift_to_entity(row) if row else None

    async def update(self, shift: Shift) -> None:
        row = await self._session.get(ShiftModel, shift.id)
        if row is None:
            raise ValueError(f"Shift {shift.id} not found")
        row.end_time = shift.end_time
        row.total_sessions = shift.total_sessions
        row.total_revenue = shift.total_revenue
        row.status = shift.status
        row.updated_at = shift.updated_at
        row.sync_version = shift.sync_version
        await self._session.flush()

    async def list_by_branch(self, branch_id: str, limit: int = 50) -> list[Shift]:
        result = await self._session.execute(
            select(ShiftModel)
            .where(ShiftModel.branch_id == branch_id)
            .order_by(ShiftModel.start_time.desc())
            .limit(limit)
        )
        return [_shift_to_entity(r) for r in result.scalars().all()]


class SQLiteAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, alert: Alert) -> None:
        self._session.add(
            AlertModel(
                id=alert.id,
                branch_id=alert.branch_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                message=alert.message,
                related_entity_id=alert.related_entity_id,
                is_acknowledged=alert.is_acknowledged,
                acknowledged_by=alert.acknowledged_by,
                acknowledged_at=alert.acknowledged_at,
                created_at=alert.created_at,
                updated_at=alert.updated_at,
                sync_version=alert.sync_version,
            )
        )
        await self._session.flush()

    async def get_by_id(self, alert_id: str) -> Alert | None:
        row = await self._session.get(AlertModel, alert_id)
        return _alert_to_entity(row) if row else None

    async def update(self, alert: Alert) -> None:
        row = await self._session.get(AlertModel, alert.id)
        if row is None:
            raise ValueError(f"Alert {alert.id} not found")
        row.is_acknowledged = alert.is_acknowledged
        row.acknowledged_by = alert.acknowledged_by
        row.acknowledged_at = alert.acknowledged_at
        row.updated_at = alert.updated_at
        row.sync_version = alert.sync_version
        await self._session.flush()

    async def list_unacknowledged(self) -> list[Alert]:
        result = await self._session.execute(
            select(AlertModel).where(AlertModel.is_acknowledged.is_(False)).order_by(AlertModel.created_at.desc())
        )
        return [_alert_to_entity(r) for r in result.scalars().all()]

    async def list_recent(self, limit: int = 100) -> list[Alert]:
        result = await self._session.execute(
            select(AlertModel).order_by(AlertModel.created_at.desc()).limit(limit)
        )
        return [_alert_to_entity(r) for r in result.scalars().all()]


class SQLiteDeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, device_id: str) -> Device | None:
        row = await self._session.get(DeviceModel, device_id)
        return _device_to_entity(row) if row else None

    async def update_status(self, device_id: str, is_online: bool) -> None:
        from datetime import datetime

        row = await self._session.get(DeviceModel, device_id)
        if row is None:
            raise ValueError(f"Device {device_id} not found")
        row.is_online = is_online
        row.last_seen_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        row.sync_version += 1
        await self._session.flush()

    async def list_all(self) -> list[Device]:
        result = await self._session.execute(select(DeviceModel))
        return [_device_to_entity(r) for r in result.scalars().all()]
