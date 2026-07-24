"""SQLAlchemy ORM models — local SQLite schema.

These are separate from domain entities on purpose (Clean Architecture):
the domain layer must not know about SQLAlchemy. Repositories translate
between ORM rows and domain entities.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, Float
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
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
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
    identity_card: Mapped[str] = mapped_column(String(50), default="")
    vehicle_type: Mapped[str] = mapped_column(String(20))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class CardModel(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    rfid_code: Mapped[str] = mapped_column(String(64), index=True)
    card_type: Mapped[str] = mapped_column(String(20), default="GUEST", index=True)
    subscriber_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
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
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
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
    # Added: links a session to the operator Shift open at entry time, so
    # CloseShiftUseCase can compute totals via list_by_shift(). Previously
    # missing, which left list_by_shift() unable to filter at all.
    shift_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
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
    """Pending records to push to the central MySQL database."""

    __tablename__ = "sync_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_table: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(36))
    operation: Mapped[str] = mapped_column(String(10))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


# ──────────────────────────────────────────────────────────────────────────
# Added: models for the repositories that already had ports/interfaces
# (IUserRepository, IShiftRepository, IAlertRepository, IDeviceRepository)
# but no SQLite table/implementation backing them yet.
# ──────────────────────────────────────────────────────────────────────────


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="OPERATOR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class ShiftModel(Base):
    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    operator_id: Mapped[str] = mapped_column(String(36), index=True)
    lane_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note: Mapped[str] = mapped_column(String(255), default="")
    opening_cash: Mapped[int] = mapped_column(Integer, default=0)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[int] = mapped_column(Integer, default=0)
    closing_cash: Mapped[int] = mapped_column(Integer, default=0)
    close_note: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class AlertModel(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    alert_type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    handle_note: Mapped[str] = mapped_column(Text, default="")
    related_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class DeviceModel(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    branch_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(120))
    device_type: Mapped[str] = mapped_column(String(20))
    connection_string: Mapped[str] = mapped_column(String(255))
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_version: Mapped[int] = mapped_column(Integer, default=1)


class RoleModel(Base):
    """Configurable role; users reference it by its unique name."""
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PermissionModel(Base):
    """A granular permission code, e.g. ``subscriber.manage``."""
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class RolePermissionModel(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    permission_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class VehicleTypeModel(Base):
    """Configurable vehicle category used across subscribers and fee rules."""
    __tablename__ = "vehicle_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SystemSettingsModel(Base):
    __tablename__ = "system_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    parking_name: Mapped[str] = mapped_column(String(100), default="Bãi Giữ Xe PMQL")
    phone: Mapped[str] = mapped_column(String(20), default="", nullable=True)
    address: Mapped[str] = mapped_column(String(200), default="", nullable=True)
    footer_text: Mapped[str] = mapped_column(String(200), default="", nullable=True)
    
    capacity_total: Mapped[int] = mapped_column(Integer, default=0)
    capacity_moto: Mapped[int] = mapped_column(Integer, default=0)
    capacity_car: Mapped[int] = mapped_column(Integer, default=0)
    capacity_truck: Mapped[int] = mapped_column(Integer, default=0)
    
    auto_barrier_delay_sec: Mapped[int] = mapped_column(Integer, default=8)
    free_time_mins: Mapped[int] = mapped_column(Integer, default=5)
    anpr_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    night_surcharge_from: Mapped[str] = mapped_column(String(10), default="22:00")
    night_surcharge_to: Mapped[str] = mapped_column(String(10), default="06:00")
    tcp_port: Mapped[int] = mapped_column(Integer, default=9001)
    
    bank_name: Mapped[str] = mapped_column(String(100), default="", nullable=True)
    bank_account_number: Mapped[str] = mapped_column(String(50), default="", nullable=True)
    bank_account_name: Mapped[str] = mapped_column(String(100), default="", nullable=True)
    
    alert_email: Mapped[str] = mapped_column(String(100), default="", nullable=True)
