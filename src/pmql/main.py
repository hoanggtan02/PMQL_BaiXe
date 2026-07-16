"""Composition root — wires use cases to concrete adapters and exposes a CLI.

This is intentionally a plain CLI (no PySide6 UI yet). It exists so the
core business flows can be exercised end-to-end against a real SQLite
file, with mock hardware standing in for camera / RFID / barrier.

Usage (from repo root, after `pip install -e .`):

    python -m pmql.main init-db
    python -m pmql.main enter --plate 51F-12345 --type motorbike
    python -m pmql.main exit --plate 51F-12345
    python -m pmql.main list-sessions
    python -m pmql.main create-user --username an.nguyen --password s3cret --full-name "An Nguyen"
    python -m pmql.main login --username an.nguyen --password s3cret
    python -m pmql.main open-shift --operator-id an.nguyen
    python -m pmql.main close-shift --operator-id an.nguyen
    python -m pmql.main register-subscriber --full-name "Le Van A" --phone 0900000000 \
        --vehicle-type motorbike --valid-from 2026-01-01 --valid-until 2026-12-31
    python -m pmql.main ack-alert --alert-id <id> --user-id an.nguyen

Previously the docstring here mentioned `list-sessions` but it (and every
other use case already implemented at the application layer) had no CLI
command registered in `build_parser()`. This composition root now wires
all of them up.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime

import structlog

from pmql.application.ports.repositories import ILaneRepository
from pmql.application.use_cases.alert_ops.acknowledge_alert_use_case import (
    AcknowledgeAlertInput,
    AcknowledgeAlertUseCase,
)
from pmql.application.use_cases.auth.create_user_use_case import CreateUserInput, CreateUserUseCase
from pmql.application.use_cases.auth.login_use_case import LoginInput, LoginUseCase
from pmql.application.use_cases.management_ops import (
    FeeRuleInput, FeeRuleManagementUseCase, SubscriberManagementUseCase,
    SubscriberUpdateInput, UserManagementUseCase, UserUpdateInput,
)
from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import (
    VehicleEntryInput,
    VehicleEntryUseCase,
)
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import (
    VehicleExitInput,
    VehicleExitUseCase,
)
from pmql.application.use_cases.shift_ops.close_shift_use_case import CloseShiftInput, CloseShiftUseCase
from pmql.application.use_cases.shift_ops.open_shift_use_case import OpenShiftInput, OpenShiftUseCase
from pmql.application.use_cases.subscriber_ops.register_subscriber_use_case import (
    RegisterSubscriberInput,
    RegisterSubscriberUseCase,
)
from pmql.config import get_settings
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.lane import Lane
from pmql.domain.entities.user import User
from pmql.domain.exceptions import DomainError
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.repositories import (
    SQLiteAlertRepository,
    SQLiteCardRepository,
    SQLiteFeeRuleRepository,
    SQLiteLaneRepository,
    SQLiteSessionRepository,
    SQLiteShiftRepository,
    SQLiteSubscriberRepository,
    SQLiteUserRepository,
    SQLiteVehicleRepository,
)
from pmql.infrastructure.security.password_hasher import PBKDF2PasswordHasher
from pmql.infrastructure.security.jwt_token_service import JwtTokenService
from pmql.infrastructure.sync.outbox_writer import SQLiteSyncOutboxWriter

log = structlog.get_logger(__name__)

DEFAULT_LANE_ID = "lane-main-in-out"


async def cmd_init_db() -> None:
    """Create tables and seed one lane + two default fee rules."""
    settings = get_settings()
    db = Database(settings.local_database_url)
    await db.create_all()

    async with db.session() as session:
        lane_repo: ILaneRepository = SQLiteLaneRepository(session)
        fee_repo = SQLiteFeeRuleRepository(session)
        user_repo = SQLiteUserRepository(session)

        if await lane_repo.get_by_id(DEFAULT_LANE_ID) is None:
            await lane_repo.create(
                Lane(
                    id=DEFAULT_LANE_ID,
                    branch_id=settings.branch_id,
                    name="Cong chinh",
                    direction="BIDIRECTIONAL",
                    is_active=True,
                )
            )
            print(f"Created default lane: {DEFAULT_LANE_ID}")

        existing_rules = {r.vehicle_type for r in await fee_repo.list_all()}
        if "motorbike" not in existing_rules:
            await fee_repo.create(
                FeeRule(
                    branch_id=settings.branch_id,
                    name="Xe may - mac dinh",
                    vehicle_type="motorbike",
                    free_minutes=10,
                    block_minutes=60,
                    price_per_block=5000,
                )
            )
            print("Created fee rule: motorbike (5,000 VND/gio, mien phi 10 phut dau)")
        if "car" not in existing_rules:
            await fee_repo.create(
                FeeRule(
                    branch_id=settings.branch_id,
                    name="O to - mac dinh",
                    vehicle_type="car",
                    free_minutes=10,
                    block_minutes=60,
                    price_per_block=20000,
                    day_max=200000,
                )
            )
            print("Created fee rule: car (20,000 VND/gio, toi da 200,000 VND/ngay)")
        if await user_repo.get_by_username("admin") is None:
            await user_repo.create(User(
                branch_id=settings.branch_id, username="admin", full_name="Quản trị viên",
                role="ADMIN", password_hash=PBKDF2PasswordHasher().hash("123"),
            ))
            print("Created default admin account: admin / 123")

    await db.dispose()
    print("Database ready at:", settings.local_database_url)


async def cmd_enter(plate: str, vehicle_type: str, rfid: str | None, shift_id: str | None) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)

    async with db.session() as session:
        use_case = VehicleEntryUseCase(
            session_repo=SQLiteSessionRepository(session),
            vehicle_repo=SQLiteVehicleRepository(session),
            card_repo=SQLiteCardRepository(session),
            fee_rule_repo=SQLiteFeeRuleRepository(session),
            subscriber_repo=SQLiteSubscriberRepository(session),
            lane_repo=SQLiteLaneRepository(session),
            barrier=MockBarrierController(),
            outbox=SQLiteSyncOutboxWriter(session),
        )
        result = await use_case.execute(
            VehicleEntryInput(
                lane_id=DEFAULT_LANE_ID,
                rfid_code=rfid,
                plate_number=plate,
                vehicle_type=vehicle_type,
                shift_id=shift_id,
            )
        )

    await db.dispose()
    print(f"Vao xe OK -> session_id={result.session_id} plate={result.plate_number} "
          f"barrier_opened={result.barrier_opened}")


async def cmd_exit(plate: str, rfid: str | None) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)

    async with db.session() as session:
        use_case = VehicleExitUseCase(
            session_repo=SQLiteSessionRepository(session),
            card_repo=SQLiteCardRepository(session),
            fee_rule_repo=SQLiteFeeRuleRepository(session),
            subscriber_repo=SQLiteSubscriberRepository(session),
            vehicle_repo=SQLiteVehicleRepository(session),
            barrier=MockBarrierController(),
            fee_calculator=FeeCalculator(),
            outbox=SQLiteSyncOutboxWriter(session),
        )
        result = await use_case.execute(VehicleExitInput(lane_id=DEFAULT_LANE_ID, rfid_code=rfid, plate_number=plate))

    await db.dispose()
    print(
        f"Ra xe OK -> session_id={result.session_id} plate={result.plate_number} "
        f"phi={result.fee_amount:,} VND thoi_gian={result.duration_minutes} phut "
        f"la_thue_bao={result.is_subscriber} barrier_opened={result.barrier_opened}"
    )


async def cmd_list_sessions(limit: int) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)

    async with db.session() as session:
        sessions = await SQLiteSessionRepository(session).list_recent(settings.branch_id, limit=limit)

    await db.dispose()
    if not sessions:
        print("Khong co phien do xe nao.")
        return
    for s in sessions:
        print(
            f"{s.id[:8]}...  plate={s.plate_number or '-':10s} status={s.status:8s} "
            f"vao={s.entry_time.isoformat(timespec='minutes')} "
            f"ra={s.exit_time.isoformat(timespec='minutes') if s.exit_time else '-':16s} "
            f"phi={s.fee_amount:,} VND"
        )


async def cmd_create_user(username: str, password: str, full_name: str, role: str) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)
    hasher = PBKDF2PasswordHasher()

    async with db.session() as session:
        use_case = CreateUserUseCase(SQLiteUserRepository(session), hasher)
        result = await use_case.execute(
            CreateUserInput(branch_id=settings.branch_id, username=username, password=password,
                            full_name=full_name, role=role)
        )

    await db.dispose()
    print(f"Tao user OK -> user_id={result.user_id} username={username} role={role}")


async def cmd_login(username: str, password: str) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)
    hasher = PBKDF2PasswordHasher()

    async with db.session() as session:
        use_case = LoginUseCase(
            SQLiteUserRepository(session), hasher,
            JwtTokenService(settings.secret_key, settings.access_token_expire_minutes),
        )
        result = await use_case.execute(LoginInput(username=username, password=password))

    await db.dispose()
    print(f"Dang nhap OK -> user_id={result.user_id} username={result.username} "
          f"role={result.role} full_name={result.full_name}")
    print(f"access_token={result.access_token}")


def cmd_ui() -> None:
    from pmql.ui.app import launch
    raise SystemExit(launch(get_settings()))


async def cmd_open_shift(operator_id: str) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)

    async with db.session() as session:
        use_case = OpenShiftUseCase(SQLiteShiftRepository(session))
        result = await use_case.execute(OpenShiftInput(branch_id=settings.branch_id, operator_id=operator_id))

    await db.dispose()
    print(f"Mo ca OK -> shift_id={result.shift_id} start_time={result.start_time}")


async def cmd_close_shift(operator_id: str) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)

    async with db.session() as session:
        use_case = CloseShiftUseCase(SQLiteShiftRepository(session), SQLiteSessionRepository(session))
        result = await use_case.execute(CloseShiftInput(operator_id=operator_id))

    await db.dispose()
    print(f"Dong ca OK -> shift_id={result.shift_id} tong_phien={result.total_sessions} "
          f"tong_doanh_thu={result.total_revenue:,} VND")


async def cmd_register_subscriber(
    full_name: str, phone: str, vehicle_type: str, valid_from: str, valid_until: str,
    email: str | None, rfid: str | None,
) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)

    async with db.session() as session:
        use_case = RegisterSubscriberUseCase(SQLiteSubscriberRepository(session), SQLiteCardRepository(session))
        result = await use_case.execute(
            RegisterSubscriberInput(
                branch_id=settings.branch_id,
                full_name=full_name,
                phone=phone,
                vehicle_type=vehicle_type,
                valid_from=date.fromisoformat(valid_from),
                valid_until=date.fromisoformat(valid_until),
                email=email,
                rfid_code=rfid,
            )
        )

    await db.dispose()
    print(f"Dang ky thue bao OK -> subscriber_id={result.subscriber_id} card_id={result.card_id}")


async def cmd_ack_alert(alert_id: str, user_id: str) -> None:
    settings = get_settings()
    db = Database(settings.local_database_url)

    async with db.session() as session:
        use_case = AcknowledgeAlertUseCase(SQLiteAlertRepository(session))
        await use_case.execute(AcknowledgeAlertInput(alert_id=alert_id, user_id=user_id))

    await db.dispose()
    print(f"Xac nhan alert OK -> alert_id={alert_id} boi user_id={user_id}")


async def cmd_list_subscribers() -> None:
    settings = get_settings(); db = Database(settings.local_database_url)
    async with db.session() as session:
        items = await SQLiteSubscriberRepository(session).list_all()
    await db.dispose()
    for item in items:
        print(f"{item.id}  {item.full_name}  {item.phone}  {item.vehicle_type}  active={item.is_active}")


async def cmd_update_subscriber(args: argparse.Namespace) -> None:
    settings = get_settings(); db = Database(settings.local_database_url)
    async with db.session() as session:
        await SubscriberManagementUseCase(SQLiteSubscriberRepository(session)).update(SubscriberUpdateInput(
            args.subscriber_id, args.full_name, args.phone, args.vehicle_type,
            date.fromisoformat(args.valid_from), date.fromisoformat(args.valid_until), args.email, not args.inactive,
        ))
    await db.dispose(); print("Cap nhat thue bao OK")


async def cmd_delete_subscriber(subscriber_id: str) -> None:
    settings = get_settings(); db = Database(settings.local_database_url)
    async with db.session() as session:
        await SubscriberManagementUseCase(SQLiteSubscriberRepository(session)).delete(subscriber_id)
    await db.dispose(); print("Xoa thue bao OK")


def _fee_input(args: argparse.Namespace, branch_id: str) -> FeeRuleInput:
    return FeeRuleInput(branch_id, args.name, args.vehicle_type, args.free_minutes, args.block_minutes,
                        args.price_per_block, args.day_max, not args.inactive)


async def cmd_fee_rule(args: argparse.Namespace) -> None:
    settings = get_settings(); db = Database(settings.local_database_url)
    async with db.session() as session:
        repo = SQLiteFeeRuleRepository(session); use_case = FeeRuleManagementUseCase(repo)
        if args.command == "list-fee-rules":
            for rule in await repo.list_all():
                print(f"{rule.id}  {rule.name}  {rule.vehicle_type}  {rule.price_per_block:,} VND/{rule.block_minutes}p active={rule.is_active}")
        elif args.command == "create-fee-rule":
            print(f"Tao bieu phi OK -> rule_id={await use_case.create(_fee_input(args, settings.branch_id))}")
        elif args.command == "update-fee-rule":
            await use_case.update(args.rule_id, _fee_input(args, settings.branch_id)); print("Cap nhat bieu phi OK")
        else:
            await use_case.delete(args.rule_id); print("Xoa bieu phi OK")
    await db.dispose()


async def cmd_user_management(args: argparse.Namespace) -> None:
    settings = get_settings(); db = Database(settings.local_database_url)
    async with db.session() as session:
        repo = SQLiteUserRepository(session); use_case = UserManagementUseCase(repo, PBKDF2PasswordHasher())
        if args.command == "list-users":
            for user in await repo.list_all():
                print(f"{user.id}  {user.username}  {user.full_name}  {user.role} active={user.is_active}")
        elif args.command == "update-user":
            await use_case.update(UserUpdateInput(args.user_id, args.full_name, args.role, not args.inactive, args.password))
            print("Cap nhat tai khoan OK")
        else:
            await use_case.delete(args.user_id); print("Xoa tai khoan OK")
    await db.dispose()


async def cmd_reset_password(username: str, password: str) -> None:
    settings = get_settings(); db = Database(settings.local_database_url)
    async with db.session() as session:
        repo = SQLiteUserRepository(session)
        user = await repo.get_by_username(username)
        if user is None:
            from pmql.domain.exceptions import UserNotFoundError
            raise UserNotFoundError(username)
        await UserManagementUseCase(repo, PBKDF2PasswordHasher()).update(
            UserUpdateInput(user.id, user.full_name, user.role, user.is_active, password)
        )
    await db.dispose(); print(f"Da doi mat khau cho {username}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pmql", description="PMQL Bai Xe — CLI demo")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create tables and seed a default lane + fee rules")

    p_enter = sub.add_parser("enter", help="Record a vehicle entry")
    p_enter.add_argument("--plate", required=True)
    p_enter.add_argument("--type", dest="vehicle_type", default="motorbike", choices=["motorbike", "car", "truck"])
    p_enter.add_argument("--rfid", default=None)
    p_enter.add_argument("--shift-id", dest="shift_id", default=None,
                         help="Operator's currently open shift id (from `open-shift`), so this "
                              "entry is counted when the shift is closed")

    p_exit = sub.add_parser("exit", help="Record a vehicle exit and compute the fee")
    p_exit.add_argument("--plate", required=False, default=None)
    p_exit.add_argument("--rfid", required=False, default=None)

    p_list = sub.add_parser("list-sessions", help="List recent parking sessions for this branch")
    p_list.add_argument("--limit", type=int, default=20)

    p_create_user = sub.add_parser("create-user", help="Provision a new operator/admin account")
    p_create_user.add_argument("--username", required=True)
    p_create_user.add_argument("--password", required=True)
    p_create_user.add_argument("--full-name", dest="full_name", required=True)
    p_create_user.add_argument("--role", default="OPERATOR", choices=["OPERATOR", "SUPERVISOR", "ADMIN"])

    p_login = sub.add_parser("login", help="Authenticate an operator by username/password")
    p_login.add_argument("--username", required=True)
    p_login.add_argument("--password", required=True)

    sub.add_parser("ui", help="Launch the PySide6 desktop login screen")

    p_open_shift = sub.add_parser("open-shift", help="Open a new work shift for an operator")
    p_open_shift.add_argument("--operator-id", dest="operator_id", required=True)

    p_close_shift = sub.add_parser("close-shift", help="Close the operator's open shift and print totals")
    p_close_shift.add_argument("--operator-id", dest="operator_id", required=True)

    p_reg_sub = sub.add_parser("register-subscriber", help="Register a monthly-pass subscriber")
    p_reg_sub.add_argument("--full-name", dest="full_name", required=True)
    p_reg_sub.add_argument("--phone", required=True)
    p_reg_sub.add_argument("--vehicle-type", dest="vehicle_type", required=True,
                           choices=["motorbike", "car", "truck"])
    p_reg_sub.add_argument("--valid-from", dest="valid_from", required=True, help="YYYY-MM-DD")
    p_reg_sub.add_argument("--valid-until", dest="valid_until", required=True, help="YYYY-MM-DD")
    p_reg_sub.add_argument("--email", default=None)
    p_reg_sub.add_argument("--rfid", default=None, help="Issue/re-link an RFID card immediately")

    sub.add_parser("list-subscribers", help="List monthly-pass subscribers")
    p_update_sub = sub.add_parser("update-subscriber", help="Edit a monthly-pass subscriber")
    p_update_sub.add_argument("--subscriber-id", required=True)
    p_update_sub.add_argument("--full-name", required=True)
    p_update_sub.add_argument("--phone", required=True)
    p_update_sub.add_argument("--vehicle-type", required=True, choices=["motorbike", "car", "truck"])
    p_update_sub.add_argument("--valid-from", required=True)
    p_update_sub.add_argument("--valid-until", required=True)
    p_update_sub.add_argument("--email", default=None)
    p_update_sub.add_argument("--inactive", action="store_true")
    p_delete_sub = sub.add_parser("delete-subscriber", help="Delete a monthly-pass subscriber")
    p_delete_sub.add_argument("--subscriber-id", required=True)

    def add_fee_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--name", required=True)
        command.add_argument("--vehicle-type", required=True, choices=["motorbike", "car", "truck"])
        command.add_argument("--free-minutes", type=int, default=10)
        command.add_argument("--block-minutes", type=int, default=60)
        command.add_argument("--price-per-block", type=int, required=True)
        command.add_argument("--day-max", type=int, default=None)
        command.add_argument("--inactive", action="store_true")

    p_create_fee = sub.add_parser("create-fee-rule", help="Create a fee rule")
    add_fee_arguments(p_create_fee)
    p_update_fee = sub.add_parser("update-fee-rule", help="Edit a fee rule")
    p_update_fee.add_argument("--rule-id", required=True)
    add_fee_arguments(p_update_fee)
    p_delete_fee = sub.add_parser("delete-fee-rule", help="Delete a fee rule")
    p_delete_fee.add_argument("--rule-id", required=True)
    sub.add_parser("list-fee-rules", help="List fee rules")

    sub.add_parser("list-users", help="List user accounts")
    p_update_user = sub.add_parser("update-user", help="Edit an account or reset its password")
    p_update_user.add_argument("--user-id", required=True)
    p_update_user.add_argument("--full-name", required=True)
    p_update_user.add_argument("--role", required=True, choices=["OPERATOR", "SUPERVISOR", "ADMIN"])
    p_update_user.add_argument("--password", default=None)
    p_update_user.add_argument("--inactive", action="store_true")
    p_delete_user = sub.add_parser("delete-user", help="Delete an account")
    p_delete_user.add_argument("--user-id", required=True)
    p_reset_password = sub.add_parser("reset-password", help="Reset a user's password")
    p_reset_password.add_argument("--username", required=True)
    p_reset_password.add_argument("--password", required=True)

    p_ack = sub.add_parser("ack-alert", help="Acknowledge a system alert")
    p_ack.add_argument("--alert-id", dest="alert_id", required=True)
    p_ack.add_argument("--user-id", dest="user_id", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "init-db":
            asyncio.run(cmd_init_db())
        elif args.command == "enter":
            asyncio.run(cmd_enter(args.plate, args.vehicle_type, args.rfid, args.shift_id))
        elif args.command == "exit":
            if not args.plate and not args.rfid:
                print("Can truyen --plate hoac --rfid", file=sys.stderr)
                sys.exit(1)
            asyncio.run(cmd_exit(args.plate, args.rfid))
        elif args.command == "list-sessions":
            asyncio.run(cmd_list_sessions(args.limit))
        elif args.command == "create-user":
            asyncio.run(cmd_create_user(args.username, args.password, args.full_name, args.role))
        elif args.command == "login":
            asyncio.run(cmd_login(args.username, args.password))
        elif args.command == "ui":
            cmd_ui()
        elif args.command == "open-shift":
            asyncio.run(cmd_open_shift(args.operator_id))
        elif args.command == "close-shift":
            asyncio.run(cmd_close_shift(args.operator_id))
        elif args.command == "register-subscriber":
            asyncio.run(
                cmd_register_subscriber(
                    args.full_name, args.phone, args.vehicle_type, args.valid_from,
                    args.valid_until, args.email, args.rfid,
                )
            )
        elif args.command == "list-subscribers":
            asyncio.run(cmd_list_subscribers())
        elif args.command == "update-subscriber":
            asyncio.run(cmd_update_subscriber(args))
        elif args.command == "delete-subscriber":
            asyncio.run(cmd_delete_subscriber(args.subscriber_id))
        elif args.command in {"list-fee-rules", "create-fee-rule", "update-fee-rule", "delete-fee-rule"}:
            asyncio.run(cmd_fee_rule(args))
        elif args.command in {"list-users", "update-user", "delete-user"}:
            asyncio.run(cmd_user_management(args))
        elif args.command == "reset-password":
            asyncio.run(cmd_reset_password(args.username, args.password))
        elif args.command == "ack-alert":
            asyncio.run(cmd_ack_alert(args.alert_id, args.user_id))
    except DomainError as exc:
        print(f"Loi nghiep vu: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
