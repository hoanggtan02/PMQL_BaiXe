from __future__ import annotations
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.authorization_repository import SQLiteAuthorizationRepository
from pmql.infrastructure.persistence.sqlite.vehicle_type_repository import SQLiteVehicleTypeRepository
from pmql.infrastructure.persistence.sqlite.repositories import (
    SQLiteAlertRepository, SQLiteCardRepository, SQLiteFeeRuleRepository,
    SQLiteLaneRepository, SQLiteSessionRepository, SQLiteShiftRepository,
    SQLiteSubscriberRepository, SQLiteUserRepository, SQLiteVehicleRepository,
)
from pmql.infrastructure.security.jwt_token_service import JwtTokenService
from pmql.infrastructure.security.password_hasher import PBKDF2PasswordHasher
from pmql.infrastructure.sync.outbox_writer import SQLiteSyncOutboxWriter

import asyncio
from datetime import date, datetime
from pmql.application.use_cases.auth.create_user_use_case import CreateUserInput, CreateUserUseCase
from pmql.application.use_cases.auth.login_use_case import LoginInput, LoginUseCase
from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import VehicleEntryInput, VehicleEntryUseCase
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import VehicleExitInput, VehicleExitUseCase
from pmql.application.use_cases.management_ops import FeeRuleInput, FeeRuleManagementUseCase, SubscriberManagementUseCase, SubscriberUpdateInput, UserManagementUseCase, UserUpdateInput, ShiftInput, ShiftManagementUseCase
from pmql.application.use_cases.subscriber_ops.register_subscriber_use_case import RegisterSubscriberInput, RegisterSubscriberUseCase
from pmql.application.use_cases.shift_ops.open_shift_use_case import OpenShiftInput, OpenShiftUseCase
from pmql.application.use_cases.shift_ops.close_shift_use_case import CloseShiftInput, CloseShiftUseCase
from pmql.config import Settings
from pmql.domain.entities.card import Card
from pmql.domain.entities.lane import Lane
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.hardware.rfid_tcp import run_rfid_server_in_thread
from PySide6.QtCore import QObject, Signal

class HardwareSignals(QObject):
    rfid_scanned = Signal(str, str)

global_hw_signals = HardwareSignals()

async def _authenticate(settings: Settings, username: str, password: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await LoginUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher(), JwtTokenService(settings.secret_key, settings.access_token_expire_minutes)).execute(LoginInput(username, password))
    finally: await db.dispose()

async def _open_shift(settings: Settings, user_id: str, lane_id: str | None = None, note: str = "", opening_cash: int = 0) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: 
            inp = OpenShiftInput(settings.branch_id, user_id, lane_id, note, opening_cash)
            return (await OpenShiftUseCase(SQLiteShiftRepository(session)).execute(inp)).shift_id
    finally: await db.dispose()

async def _close_shift(settings: Settings, user_id: str, actual_ending_cash: int | None, closing_notes: str | None):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await CloseShiftUseCase(SQLiteShiftRepository(session), SQLiteSessionRepository(session)).execute(CloseShiftInput(user_id, actual_ending_cash, closing_notes))
    finally: await db.dispose()

async def _entry(settings: Settings, lane_id: str, plate: str, vehicle: str, shift_id: str) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            output = await VehicleEntryUseCase(SQLiteSessionRepository(session), SQLiteVehicleRepository(session), SQLiteCardRepository(session), SQLiteFeeRuleRepository(session), SQLiteSubscriberRepository(session), SQLiteLaneRepository(session), MockBarrierController(), SQLiteSyncOutboxWriter(session)).execute(VehicleEntryInput(lane_id, plate_number=plate, vehicle_type=vehicle, shift_id=shift_id)); return output.session_id
    finally: await db.dispose()

async def _exit(settings: Settings, lane_id: str, plate: str) -> tuple[int, int]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            output = await VehicleExitUseCase(SQLiteSessionRepository(session), SQLiteCardRepository(session), SQLiteFeeRuleRepository(session), SQLiteSubscriberRepository(session), SQLiteVehicleRepository(session), MockBarrierController(), FeeCalculator(), SQLiteSyncOutboxWriter(session)).execute(VehicleExitInput(lane_id, plate_number=plate)); return output.fee_amount, output.duration_minutes
    finally: await db.dispose()

async def _users(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteUserRepository(session).list_all()
    finally: await db.dispose()

async def _create_user(settings: Settings, username: str, password: str, full_name: str, role: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await CreateUserUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher()).execute(CreateUserInput(settings.branch_id, username, password, full_name, role))
    finally: await db.dispose()

async def _update_user(settings: Settings, user_id: str, full_name: str, role: str, is_active: bool, password: str | None) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await UserManagementUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher()).update(UserUpdateInput(user_id, full_name, role, is_active, password))
    finally: await db.dispose()

async def _delete_user(settings: Settings, user_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await UserManagementUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher()).delete(user_id)
    finally: await db.dispose()

async def _create_subscriber(settings: Settings, full_name: str, phone: str, email: str | None, identity_card: str, vehicles: list[dict[str, str]], valid_from: str, valid_until: str, rfid_code: str | None) -> None:
    if not full_name.strip() or not phone.strip(): raise ValueError("Họ tên và số điện thoại là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await RegisterSubscriberUseCase(SQLiteSubscriberRepository(session), SQLiteCardRepository(session), SQLiteVehicleRepository(session)).execute(RegisterSubscriberInput(settings.branch_id, full_name.strip(), phone.strip(), identity_card.strip(), vehicles, date.fromisoformat(valid_from), date.fromisoformat(valid_until), email, rfid_code))
    finally: await db.dispose()

async def _create_fee_rule(settings: Settings, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None, is_active: bool = True) -> None:
    if not name.strip(): raise ValueError("Tên quy tắc là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteFeeRuleRepository(session)
            rule = FeeRuleInput(settings.branch_id, name.strip(), vehicle_type, free_minutes, block_minutes, price_per_block, day_max)
            rule_id = await FeeRuleManagementUseCase(repo).create(rule)
            created = await repo.get_by_id(rule_id)
            if created is not None:
                created.night_surcharge = night_surcharge or None
                await repo.update(created)
    finally: await db.dispose()

async def _update_fee_rule(settings: Settings, rule_id: str, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None, is_active: bool = True) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteFeeRuleRepository(session)
            await FeeRuleManagementUseCase(repo).update(rule_id, FeeRuleInput(settings.branch_id, name, vehicle_type, free_minutes, block_minutes, price_per_block, day_max, is_active))
            rule = await repo.get_by_id(rule_id)
            if rule is not None:
                rule.night_surcharge = night_surcharge or None
                await repo.update(rule)
    finally: await db.dispose()

async def _delete_fee_rule(settings: Settings, rule_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await FeeRuleManagementUseCase(SQLiteFeeRuleRepository(session)).delete(rule_id)
    finally: await db.dispose()

async def _stats(settings: Settings, shift_id: str | None) -> dict[str, object]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            sessions = await SQLiteSessionRepository(session).list_recent(settings.branch_id, 500)
            users = await SQLiteUserRepository(session).list_all()
            lanes = await SQLiteLaneRepository(session).list_active(settings.branch_id)
        active = [s for s in sessions if s.status == "ACTIVE"]
        today = date.today()
        closed = [s for s in sessions if s.exit_time and s.exit_time.date() == today]
        # Build sessions_detail for live table
        now = datetime.now()
        def fmt_duration(entry_time):
            diff = now - entry_time
            h = int(diff.total_seconds() // 3600)
            m = int((diff.total_seconds() % 3600) // 60)
            return f"{h}g {m}p" if h else f"{m}p"
        sessions_detail = []
        for s in active:
            sessions_detail.append({
                "plate": s.plate_number or "RFID",
                "vehicle_type": getattr(s, 'vehicle_type', 'Xe máy'),
                "entry_time": s.entry_time.strftime("%H:%M:%S %d/%m/%Y"),
                "duration": fmt_duration(s.entry_time),
            })
        return {
            "active": len(active),
            "plates": [s.plate_number for s in active if s.plate_number],
            "sessions_detail": sessions_detail,
            "today_count": len([s for s in sessions if s.entry_time.date() == today]),
            "revenue": sum(s.fee_amount for s in closed),
            "users": len([u for u in users if u.is_active]),
            "subscriber_count": 0,
            "lane_total": len(lanes),
            "lane_active": len(lanes),
            "alerts": 0,
        }
    finally: await db.dispose()

async def _session_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteSessionRepository(session).list_recent(settings.branch_id, 100)
        return [(s.plate_number or "RFID", s.status, s.entry_time.strftime("%d/%m %H:%M"), s.exit_time.strftime("%d/%m %H:%M") if s.exit_time else "—", f"{s.fee_amount:,} đ") for s in rows]
    finally: await db.dispose()

async def _subscriber_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteSubscriberRepository(session).list_all()
        return [(s.full_name, s.phone, s.vehicle_type, s.valid_until.isoformat(), "Hoạt động" if s.is_active else "Đã khóa") for s in rows]
    finally: await db.dispose()

async def _subscriber_entities(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteSubscriberRepository(session).list_all()
    finally: await db.dispose()

async def _subscriber_with_vehicles(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            subscribers = await SQLiteSubscriberRepository(session).list_all()
            vehicles = []
            for sub in subscribers:
                sub_vehicles = await SQLiteVehicleRepository(session).list_by_subscriber(sub.id)
                vehicles.append(sub_vehicles)
            return list(zip(subscribers, vehicles))
    finally: await db.dispose()

async def _update_subscriber(settings: Settings, subscriber_id: str, full_name: str, phone: str, email: str | None, identity_card: str, vehicles: list[dict[str, str]], valid_from: str, valid_until: str, is_active: bool) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await SubscriberManagementUseCase(SQLiteSubscriberRepository(session), SQLiteVehicleRepository(session)).update(SubscriberUpdateInput(subscriber_id, full_name, phone, identity_card, vehicles, date.fromisoformat(valid_from), date.fromisoformat(valid_until), email, is_active))
    finally: await db.dispose()

async def _delete_subscriber(settings: Settings, subscriber_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await SubscriberManagementUseCase(SQLiteSubscriberRepository(session), SQLiteVehicleRepository(session)).delete(subscriber_id)
    finally: await db.dispose()

async def _card_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteCardRepository(session).list_all()
        return [(c.rfid_code, c.subscriber_id or "—", c.vehicle_id or "—", "Hoạt động" if c.is_active else "Đã khóa") for c in rows]
    finally: await db.dispose()

async def _card_entities(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteCardRepository(session).list_all()
    finally: await db.dispose()

async def _card_display_rows(settings: Settings):
    """Resolve internal foreign keys to end-user labels before rendering UI."""
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            cards = await SQLiteCardRepository(session).list_all()
            subscribers = {item.id: item for item in await SQLiteSubscriberRepository(session).list_all()}
        rows = []
        for card in cards:
            subscriber = subscribers.get(card.subscriber_id or "")
            display = f"{subscriber.full_name} · {subscriber.phone}" if subscriber else "Chưa gán thuê bao"
            rows.append((card, display))
        return rows
    finally: await db.dispose()

async def _create_card(settings: Settings, rfid_code: str, card_type: str, subscriber_id: str | None) -> None:
    if not rfid_code.strip(): raise ValueError("Mã UID là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteCardRepository(session)
            if await repo.get_by_rfid_code(rfid_code.strip()): raise ValueError("Mã UID đã tồn tại")
            await repo.create(Card(branch_id=settings.branch_id, rfid_code=rfid_code.strip(), card_type=card_type, subscriber_id=subscriber_id, status="AVAILABLE"))
    finally: await db.dispose()

async def _update_card(settings: Settings, card_id: str, card_type: str, subscriber_id: str | None, status: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteCardRepository(session); card = await repo.get_by_id(card_id)
            if card is None: raise ValueError("Không tìm thấy thẻ")
            card.card_type, card.subscriber_id, card.status = card_type, subscriber_id, status
            await repo.update(card)
    finally: await db.dispose()

async def _delete_card(settings: Settings, card_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await SQLiteCardRepository(session).delete(card_id)
    finally: await db.dispose()

async def _lanes(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteLaneRepository(session).list_all()
    finally: await db.dispose()

async def _create_lane(settings: Settings, name: str, direction: str, camera: str | None, rfid: str | None, barrier: str | None) -> None:
    if not name.strip(): raise ValueError("Tên làn là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await SQLiteLaneRepository(session).create(Lane(branch_id=settings.branch_id, name=name.strip(), direction=direction, camera_source=camera, rfid_device_id=rfid, barrier_device_id=barrier))
    finally: await db.dispose()

async def _update_lane(settings: Settings, lane_id: str, name: str, direction: str, camera: str | None, rfid: str | None, barrier: str | None, is_active: bool) -> None:
    if not name.strip(): raise ValueError("Tên làn là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteLaneRepository(session); lane = await repo.get_by_id(lane_id)
            if lane is None: raise ValueError("Không tìm thấy làn")
            lane.name, lane.direction = name.strip(), direction
            lane.camera_source, lane.rfid_device_id, lane.barrier_device_id, lane.is_active = camera, rfid, barrier, is_active
            await repo.update(lane)
    finally: await db.dispose()

async def _delete_lane(settings: Settings, lane_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            active_sessions = await SQLiteSessionRepository(session).list_recent(settings.branch_id, 10000)
            if any(item.status == "ACTIVE" and item.lane_in_id == lane_id for item in active_sessions):
                raise ValueError("Không thể xóa làn đang có xe trong bãi")
            await SQLiteLaneRepository(session).delete(lane_id)
    finally: await db.dispose()

async def _shift_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            rows = await SQLiteShiftRepository(session).list_by_branch(settings.branch_id, 100)
            users = {item.id: item.full_name for item in await SQLiteUserRepository(session).list_all()}
        return [(users.get(s.operator_id, "Nhân viên không còn hoạt động"), s.start_time.strftime("%d/%m %H:%M"), s.end_time.strftime("%d/%m %H:%M") if s.end_time else "—", f"{s.total_revenue:,} đ", s.status) for s in rows]
    finally: await db.dispose()

async def _shift_entities(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteShiftRepository(session).list_by_branch(settings.branch_id, 100)
    finally: await db.dispose()

async def _create_shift(settings: Settings, inp: ShiftInput) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await ShiftManagementUseCase(SQLiteShiftRepository(session)).create(inp)
    finally: await db.dispose()

async def _update_shift(settings: Settings, shift_id: str, inp: ShiftInput) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await ShiftManagementUseCase(SQLiteShiftRepository(session)).update(shift_id, inp)
    finally: await db.dispose()

async def _delete_shift(settings: Settings, shift_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await ShiftManagementUseCase(SQLiteShiftRepository(session)).delete(shift_id)
    finally: await db.dispose()

async def _close_shift(settings: Settings, operator_id: str, closing_cash: int = 0, close_note: str = "") -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await CloseShiftUseCase(SQLiteShiftRepository(session), SQLiteSessionRepository(session)).execute(CloseShiftInput(operator_id, closing_cash, close_note))
    finally: await db.dispose()

async def _alert_stats(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteAlertRepository(session).get_stats()
    finally:
        await db.dispose()

async def _alert_list(settings: Settings, status: str, severity: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteAlertRepository(session).list_filtered(status, severity)
    finally:
        await db.dispose()

async def _handle_alert(settings: Settings, alert_id: str, note: str, handled_by: str = "admin"):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteAlertRepository(session)
            alert = await repo.get_by_id(alert_id)
            if alert:
                alert.is_acknowledged = True
                alert.handle_note = note
                alert.acknowledged_by = handled_by
                from datetime import datetime
                alert.acknowledged_at = datetime.utcnow()
                await repo.update(alert)
    finally:
        await db.dispose()

async def _dismiss_alert(settings: Settings, alert_id: str):
    await _handle_alert(settings, alert_id, "", "admin")

async def _handle_all_open_alerts(settings: Settings, handled_by: str = "admin"):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteAlertRepository(session)
            open_alerts = await repo.list_unacknowledged()
            from datetime import datetime
            now = datetime.utcnow()
            for alert in open_alerts:
                alert.is_acknowledged = True
                alert.handle_note = "Batch handled"
                alert.acknowledged_by = handled_by
                alert.acknowledged_at = now
                await repo.update(alert)
    finally:
        await db.dispose()

async def _open_barrier_alert(settings: Settings, lane_id: str):
    # Call the hardware layer to open barrier
    await MockBarrierController().open_barrier(lane_id)

async def _fee_rules(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteFeeRuleRepository(session).list_all()
    finally: await db.dispose()

async def _vehicle_types(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteVehicleTypeRepository(session).list_all()
    finally: await db.dispose()

async def _vehicle_name_map(settings: Settings) -> dict[str, str]:
    return {item.code: item.display_name for item in await _vehicle_types(settings)}

async def _create_vehicle_type(settings: Settings, code: str, display_name: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteVehicleTypeRepository(session).create(code, display_name)
    finally: await db.dispose()

async def _update_vehicle_type(settings: Settings, item_id: str, code: str, display_name: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteVehicleTypeRepository(session).update(item_id, code, display_name)
    finally: await db.dispose()

async def _delete_vehicle_type(settings: Settings, item_id: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            types = await SQLiteVehicleTypeRepository(session).list_all()
            current = next((item for item in types if item.id == item_id), None)
            if current is None: raise ValueError("Không tìm thấy loại xe")
            subscribers = await SQLiteSubscriberRepository(session).list_all()
            fee_rules = await SQLiteFeeRuleRepository(session).list_all()
            if any(item.vehicle_type == current.code for item in subscribers) or any(item.vehicle_type == current.code for item in fee_rules):
                raise ValueError("Không thể xóa loại xe đang được dùng trong thuê bao hoặc biểu phí")
            await SQLiteVehicleTypeRepository(session).delete(item_id)
    finally: await db.dispose()

async def _roles(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteAuthorizationRepository(session); await repo.ensure_starter_roles(); return await repo.list_roles()
    finally: await db.dispose()

async def _permissions(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteAuthorizationRepository(session).list_permissions()
    finally: await db.dispose()

async def _create_permission(settings: Settings, code: str, description: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteAuthorizationRepository(session).create_permission(code, description)
    finally: await db.dispose()

async def _role_permissions(settings: Settings, role_name: str) -> set[str]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteAuthorizationRepository(session)
            await repo.ensure_starter_roles()
            for role in await repo.list_roles():
                if role.name == role_name:
                    return set(role.permission_codes)
            return set()
    finally: await db.dispose()

async def _save_role(settings: Settings, name: str, description: str, codes: set[str]):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteAuthorizationRepository(session).save_role(name, description, codes)
    finally: await db.dispose()
async def _load_sys_settings(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        from pmql.infrastructure.persistence.sqlite.repositories import SQLiteSettingsRepository
        async with db.session() as session:
            return await SQLiteSettingsRepository(session).get_settings()
    finally:
        await db.dispose()

async def _save_sys_settings(settings: Settings, data: dict):
    db = Database(settings.local_database_url)
    try:
        from pmql.infrastructure.persistence.sqlite.repositories import SQLiteSettingsRepository
        async with db.session() as session:
            await SQLiteSettingsRepository(session).save_settings(data)
    finally:
        await db.dispose()

async def _list_devices(settings: Settings):
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    from sqlalchemy import select
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            rows = (await session.execute(select(DeviceModel).where(DeviceModel.branch_id == settings.branch_id))).scalars().all()
            return list(rows)
    finally:
        await db.dispose()

async def _save_device(settings: Settings, device_type: str, protocol: str, lane_id: str, name: str):
    import uuid
    from datetime import datetime
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            dev = DeviceModel(
                id=str(uuid.uuid4()),
                branch_id=settings.branch_id,
                name=name or f"{device_type} - {protocol}",
                device_type=device_type,
                connection_string=f"protocol={protocol};lane={lane_id}",
                is_online=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                sync_version=1
            )
            session.add(dev)
    finally:
        await db.dispose()

async def _delete_device(settings: Settings, device_id: str):
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            dev = await session.get(DeviceModel, device_id)
            if dev:
                await session.delete(dev)
    finally:
        await db.dispose()

async def _get_cards_for_subscriber(settings: Settings, subscriber_id: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            cards = await SQLiteCardRepository(session).list_all()
            return [c for c in cards if c.subscriber_id == subscriber_id]
    finally:
        await db.dispose()

async def _extend_subscriber(settings: Settings, subscriber_id: str, new_date):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteSubscriberRepository(session)
            sub = await repo.get_by_id(subscriber_id)
            if not sub: raise ValueError("Không tìm thấy thuê bao")
            sub.valid_until = new_date
            await repo.update(sub)
    finally:
        await db.dispose()

__all__ = ['Database', 'HardwareSignals', 'global_hw_signals', '_authenticate', '_open_shift', '_close_shift', '_entry', '_exit', '_users', '_create_user', '_update_user', '_delete_user', '_create_subscriber', '_create_fee_rule', '_update_fee_rule', '_delete_fee_rule', '_stats', '_session_rows', '_subscriber_rows', '_subscriber_entities', '_subscriber_with_vehicles', '_update_subscriber', '_delete_subscriber', '_card_rows', '_card_entities', '_card_display_rows', '_create_card', '_update_card', '_delete_card', '_lanes', '_create_lane', '_update_lane', '_delete_lane', '_shift_rows', '_shift_entities', '_create_shift', '_update_shift', '_delete_shift', '_close_shift', '_alert_stats', '_alert_list', '_handle_alert', '_dismiss_alert', '_handle_all_open_alerts', '_open_barrier_alert', '_fee_rules', '_vehicle_types', '_vehicle_name_map', '_create_vehicle_type', '_update_vehicle_type', '_delete_vehicle_type', '_roles', '_permissions', '_create_permission', '_role_permissions', '_save_role', '_load_sys_settings', '_save_sys_settings', '_list_devices', '_save_device', '_delete_device', '_get_cards_for_subscriber', '_extend_subscriber']
