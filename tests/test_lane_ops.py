from __future__ import annotations
import pytest
from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import VehicleEntryInput, VehicleEntryUseCase
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import VehicleExitInput, VehicleExitUseCase
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.lane import Lane
from pmql.domain.exceptions import VehicleAlreadyInsideError
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.repositories import (
    SQLiteCardRepository, SQLiteFeeRuleRepository, SQLiteLaneRepository,
    SQLiteSessionRepository, SQLiteSubscriberRepository, SQLiteVehicleRepository,
)
from pmql.infrastructure.sync.outbox_writer import SQLiteSyncOutboxWriter
from pmql.infrastructure.persistence.sqlite.models import ParkingSessionModel

LANE_ID = "test-lane"


async def backdate_entry(db, session_id, minutes_ago):
    from datetime import datetime, timedelta
    async with db.session() as session:
        row = await session.get(ParkingSessionModel, session_id)
        row.entry_time = datetime.utcnow() - timedelta(minutes=minutes_ago)


@pytest.fixture
async def db(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    await database.create_all()
    async with database.session() as session:
        await SQLiteLaneRepository(session).create(Lane(id=LANE_ID, branch_id="branch-1", name="Test Lane", direction="BIDIRECTIONAL"))
        await SQLiteFeeRuleRepository(session).create(FeeRule(branch_id="branch-1", name="motorbike", vehicle_type="motorbike", free_minutes=0, block_minutes=60, price_per_block=5000))
        await SQLiteFeeRuleRepository(session).create(FeeRule(branch_id="branch-1", name="car", vehicle_type="car", free_minutes=0, block_minutes=60, price_per_block=20000))
    yield database
    await database.dispose()


async def enter_vehicle(db, plate, vehicle_type):
    async with db.session() as session:
        use_case = VehicleEntryUseCase(
            session_repo=SQLiteSessionRepository(session), vehicle_repo=SQLiteVehicleRepository(session),
            card_repo=SQLiteCardRepository(session), fee_rule_repo=SQLiteFeeRuleRepository(session),
            subscriber_repo=SQLiteSubscriberRepository(session), lane_repo=SQLiteLaneRepository(session),
            barrier=MockBarrierController(), outbox=SQLiteSyncOutboxWriter(session),
        )
        result = await use_case.execute(VehicleEntryInput(lane_id=LANE_ID, plate_number=plate, vehicle_type=vehicle_type))
        return result.session_id


async def exit_vehicle(db, plate):
    async with db.session() as session:
        use_case = VehicleExitUseCase(
            session_repo=SQLiteSessionRepository(session), card_repo=SQLiteCardRepository(session),
            fee_rule_repo=SQLiteFeeRuleRepository(session), subscriber_repo=SQLiteSubscriberRepository(session),
            vehicle_repo=SQLiteVehicleRepository(session), barrier=MockBarrierController(),
            fee_calculator=FeeCalculator(), outbox=SQLiteSyncOutboxWriter(session),
        )
        return await use_case.execute(VehicleExitInput(lane_id=LANE_ID, plate_number=plate))


@pytest.mark.asyncio
async def test_car_is_billed_at_car_rate_not_motorbike_rate(db):
    session_id = await enter_vehicle(db, plate="51F-11111", vehicle_type="car")
    await backdate_entry(db, session_id, minutes_ago=90)
    result = await exit_vehicle(db, plate="51F-11111")
    assert result.fee_amount == 40000


@pytest.mark.asyncio
async def test_duplicate_entry_is_rejected(db):
    await enter_vehicle(db, plate="51F-33333", vehicle_type="motorbike")
    with pytest.raises(VehicleAlreadyInsideError):
        await enter_vehicle(db, plate="51F-33333", vehicle_type="motorbike")
