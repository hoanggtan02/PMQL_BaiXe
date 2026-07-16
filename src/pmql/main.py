"""Composition root — wires use cases to concrete adapters and exposes a CLI.

This is intentionally a plain CLI (no PySide6 UI yet). It exists so the
core business flow — vào xe / ra xe / tính phí — can be exercised
end-to-end against a real SQLite file, with mock hardware standing in
for camera / RFID / barrier.

Usage (from repo root, after `pip install -e .`):

    python -m pmql.main init-db
    python -m pmql.main enter --plate 51F-12345 --type motorbike
    python -m pmql.main exit --plate 51F-12345
    python -m pmql.main list-sessions
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import structlog

from pmql.application.ports.repositories import ILaneRepository
from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import (
    VehicleEntryInput,
    VehicleEntryUseCase,
)
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import (
    VehicleExitInput,
    VehicleExitUseCase,
)
from pmql.config import get_settings
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.lane import Lane
from pmql.domain.exceptions import DomainError
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.repositories import (
    SQLiteCardRepository,
    SQLiteFeeRuleRepository,
    SQLiteLaneRepository,
    SQLiteSessionRepository,
    SQLiteSubscriberRepository,
    SQLiteVehicleRepository,
)
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

    await db.dispose()
    print("Database ready at:", settings.local_database_url)


async def cmd_enter(plate: str, vehicle_type: str, rfid: str | None) -> None:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pmql", description="PMQL Bai Xe — CLI demo")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create tables and seed a default lane + fee rules")

    p_enter = sub.add_parser("enter", help="Record a vehicle entry")
    p_enter.add_argument("--plate", required=True)
    p_enter.add_argument("--type", dest="vehicle_type", default="motorbike", choices=["motorbike", "car", "truck"])
    p_enter.add_argument("--rfid", default=None)

    p_exit = sub.add_parser("exit", help="Record a vehicle exit and compute the fee")
    p_exit.add_argument("--plate", required=False, default=None)
    p_exit.add_argument("--rfid", required=False, default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "init-db":
            asyncio.run(cmd_init_db())
        elif args.command == "enter":
            asyncio.run(cmd_enter(args.plate, args.vehicle_type, args.rfid))
        elif args.command == "exit":
            if not args.plate and not args.rfid:
                print("Can truyen --plate hoac --rfid", file=sys.stderr)
                sys.exit(1)
            asyncio.run(cmd_exit(args.plate, args.rfid))
    except DomainError as exc:
        print(f"Loi nghiep vu: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
