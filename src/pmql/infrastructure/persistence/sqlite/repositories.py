"""Concrete repository implementations backed by the local SQLite database.

Each class implements the corresponding interface from
`pmql.application.ports.repositories`. All of them share one
`AsyncSession` instance so a use case's writes are part of a single
transaction (see `Database.session()`).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pmql.domain.entities.card import Card
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.lane import Lane
from pmql.domain.entities.session import ParkingSession
from pmql.domain.entities.subscriber import Subscriber
from pmql.domain.entities.vehicle import Vehicle
from pmql.infrastructure.persistence.sqlite.models import (
    CardModel,
    FeeRuleModel,
    LaneModel,
    ParkingSessionModel,
    SubscriberModel,
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


# ──────────────────────────────────────────────────────────────────────────
# Repositories
# ──────────────────────────────────────────────────────────────────────────


class SQLiteLaneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lane_id: str) -> Lane | None:
        row = await self._session.get(LaneModel, lane_id)
        return _lane_to_entity(row) if row else None

    async def list_active(self) -> list[Lane]:
        result = await self._session.execute(select(LaneModel).where(LaneModel.is_active.is_(True)))
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
        result = await self._session.execute(select(CardModel).where(CardModel.rfid_code == rfid_code))
        row = result.scalars().first()
        return _card_to_entity(row) if row else None

    async def get_by_id(self, card_id: str) -> Card | None:
        row = await self._session.get(CardModel, card_id)
        return _card_to_entity(row) if row else None

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
        result = await self._session.execute(select(CardModel).where(CardModel.subscriber_id == subscriber_id))
        return [_card_to_entity(r) for r in result.scalars().all()]


class SQLiteSubscriberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, subscriber_id: str) -> Subscriber | None:
        row = await self._session.get(SubscriberModel, subscriber_id)
        return _subscriber_to_entity(row) if row else None

    async def get_by_vehicle_type(self, vehicle_type: str, is_active: bool = True) -> list[Subscriber]:
        result = await self._session.execute(
            select(SubscriberModel).where(
                SubscriberModel.vehicle_type == vehicle_type,
                SubscriberModel.is_active.is_(is_active),
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
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()

    async def list_all(self) -> list[Subscriber]:
        result = await self._session.execute(select(SubscriberModel))
        return [_subscriber_to_entity(r) for r in result.scalars().all()]


class SQLiteFeeRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_vehicle_type(self, vehicle_type: str) -> FeeRule | None:
        result = await self._session.execute(
            select(FeeRuleModel).where(
                FeeRuleModel.vehicle_type == vehicle_type,
                FeeRuleModel.is_active.is_(True),
            )
        )
        row = result.scalars().first()
        return _fee_rule_to_entity(row) if row else None

    async def get_by_id(self, rule_id: str) -> FeeRule | None:
        row = await self._session.get(FeeRuleModel, rule_id)
        return _fee_rule_to_entity(row) if row else None

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

    async def list_all(self) -> list[FeeRule]:
        result = await self._session.execute(select(FeeRuleModel))
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
        # NOTE: shift_id linkage isn't modeled on sessions yet — returning
        # all sessions for now. Revisit once Shift <-> Session FK is added.
        result = await self._session.execute(select(ParkingSessionModel))
        return [_session_to_entity(r) for r in result.scalars().all()]
