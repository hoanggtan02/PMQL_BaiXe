"""Integration tests: VehicleEntryUseCase + VehicleExitUseCase against a real
(temp-file) SQLite database, using mock hardware. These exercise the full
wiring used by `pmql.main` and guard against regressions of two bugs fixed
in review:

1. Exit fee previously always used the 'motorbike' rate regardless of the
   vehicle's real type (cars/trucks were undercharged).
2. A vehicle could be recorded as entering twice with no active-session
   check (duplicate ACTIVE sessions for the same plate).
"""

from __future__ import annotations

import pytest

from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import (
    VehicleEntryInput,
    VehicleEntryUseCase,
)
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import (
    VehicleExitInput,
    VehicleExitUseCase,
)
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.lane import Lane
from pmql.domain.exceptions import VehicleAlreadyInsideError
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
from pmql.infrastructure.persistence.sqlite.models import ParkingSessionModel

LANE_ID = "test-lane"


async def backdate_entry(db: Database, session_id: str, minutes_ago: int) -> None:
    """Test helper: push a session's entry_time into the past so a real,
    non-zero billable duration exists (real elapsed wall-clock time between
    enter_vehicle() and exit_vehicle() in a test is ~0ms, which is not
    representative of an actual parking stay)."""
    from datetime import datetime, timedelta

    async with db.session() as session:
        row = await session.get(ParkingSessionModel, session_id)
        row.entry_time = datetime.utcnow() - timedelta(minutes=minutes_ago)


@pytest.fixture
async def db(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    await database.create_all()

    async with database.session() as session:
        await SQLiteLaneRepository(session).create(
            Lane(id=LANE_ID, branch_id="branch-1", name="Test Lane", direction="BIDIRECTIONAL")
        )
        await SQLiteFeeRuleRepository(session).create(
            FeeRule(
                branch_id="branch-1",
                name="motorbike",
                vehicle_type="motorbike",
                free_minutes=0,
                block_minutes=60,
                price_per_block=5000,
            )
        )
        await SQLiteFeeRuleRepository(session).create(
            FeeRule(
                branch_id="branch-1",
                name="car",
                vehicle_type="car",
                free_minutes=0,
                block_minutes=60,
                price_per_block=20000,
            )
        )

    yield database
    await database.dispose()


async def enter_vehicle(db: Database, plate: str, vehicle_type: str) -> str:
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
            VehicleEntryInput(lane_id=LANE_ID, plate_number=plate, vehicle_type=vehicle_type)
        )
        return result.session_id


async def exit_vehicle(db: Database, plate: str):
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
        return await use_case.execute(VehicleExitInput(lane_id=LANE_ID, plate_number=plate))


@pytest.mark.asyncio
async def test_car_is_billed_at_car_rate_not_motorbike_rate(db: Database) -> None:
    """Regression test for the fixed bug: exit must use the vehicle's real type."""
    session_id = await enter_vehicle(db, plate="51F-11111", vehicle_type="car")
    await backdate_entry(db, session_id, minutes_ago=90)  # simulate a 90-min stay

    result = await exit_vehicle(db, plate="51F-11111")

    # 90 minutes -> 2 blocks. Must be billed at the CAR rate (2 * 20,000 =
    # 40,000), never the motorbike rate (2 * 5,000 = 10,000).
    assert result.fee_amount == 40000


@pytest.mark.asyncio
async def test_motorbike_is_billed_at_motorbike_rate(db: Database) -> None:
    session_id = await enter_vehicle(db, plate="51F-22222", vehicle_type="motorbike")
    await backdate_entry(db, session_id, minutes_ago=90)

    result = await exit_vehicle(db, plate="51F-22222")

    assert result.fee_amount == 10000


@pytest.mark.asyncio
async def test_duplicate_entry_is_rejected(db: Database) -> None:
    """Regression test for the fixed bug: a plate already ACTIVE can't enter again."""
    await enter_vehicle(db, plate="51F-33333", vehicle_type="motorbike")

    with pytest.raises(VehicleAlreadyInsideError):
        await enter_vehicle(db, plate="51F-33333", vehicle_type="motorbike")


@pytest.mark.asyncio
async def test_entry_then_exit_closes_session(db: Database) -> None:
    session_id = await enter_vehicle(db, plate="51F-44444", vehicle_type="motorbike")

    result = await exit_vehicle(db, plate="51F-44444")

    assert result.session_id == session_id
    assert result.barrier_opened is True
