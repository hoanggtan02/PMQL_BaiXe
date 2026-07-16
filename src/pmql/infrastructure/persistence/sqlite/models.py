"""SQLAlchemy ORM models — local SQLite schema.

These are separate from domain entities on purpose (Clean Architecture):
the domain layer must not know about SQLAlchemy. Repositories translate
between ORM rows and domain entities.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all local ORM models."""


class LaneModel(Base):
    __tablename__ = "lanes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(120))
    direction: Mapped[str] = mapped_column(String(20), default="IN")
    camera_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rfid_device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    barrier_device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class VehicleModel(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    plate_number: Mapped[str] = mapped_column(String(20), index=True)
    vehicle_type: Mapped[str] = mapped_column(String(20))
    rfid_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subscriber_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class SubscriberModel(Base):
    __tablename__ = "subscribers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    vehicle_type: Mapped[str] = mapped_column(String(20))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class CardModel(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    rfid_code: Mapped[str] = mapped_column(String(64), index=True)
    subscriber_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class FeeRuleModel(Base):
    __tablename__ = "fee_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(120))
    vehicle_type: Mapped[str] = mapped_column(String(20), index=True)
    free_minutes: Mapped[int] = mapped_column(Integer, default=10)
    block_minutes: Mapped[int] = mapped_column(Integer, default=60)
    price_per_block: Mapped[int] = mapped_column(Integer, default=5000)
    day_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    night_surcharge: Mapped[int | None] = mapped_column(Integer, nullable=True)
    night_start_hour: Mapped[int] = mapped_column(Integer, default=22)
    night_end_hour: Mapped[int] = mapped_column(Integer, default=6)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class ParkingSessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    lane_in_id: Mapped[str] = mapped_column(String(36))
    lane_out_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(20), index=True)
    rfid_card_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    subscriber_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fee_rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    fee_amount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    entry_plate_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exit_plate_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class SyncOutboxModel(Base):
    """Pending records to push to the central MySQL database.

    Written in the SAME transaction as the business write so that a
    crash can never lose a sync event (the classic "transactional
    outbox" pattern).
    """

    __tablename__ = "sync_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_table: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(36))
    operation: Mapped[str] = mapped_column(String(10))  # INSERT | UPDATE | DELETE
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
