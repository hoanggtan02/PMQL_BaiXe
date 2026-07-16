"""Integration tests for the newly added shift, auth and RFID-exit-bugfix behavior."""

from __future__ import annotations

import pytest

from pmql.application.use_cases.auth.create_user_use_case import CreateUserInput, CreateUserUseCase
from pmql.application.use_cases.auth.login_use_case import LoginInput, LoginUseCase
from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import VehicleEntryInput, VehicleEntryUseCase
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import VehicleExitInput, VehicleExitUseCase
from pmql.application.use_cases.shift_ops.close_shift_use_case import CloseShiftInput, CloseShiftUseCase
from pmql.application.use_cases.shift_ops.open_shift_use_case import OpenShiftInput, OpenShiftUseCase
from pmql.domain.entities.card import Card
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.lane import Lane
from pmql.domain.exceptions import InvalidCredentialsError, ShiftAlreadyOpenError, UsernameAlreadyExistsError
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.models import ParkingSessionModel
from pmql.infrastructure.persistence.sqlite.repositories import (
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
from pmql.infrastructure.sync.outbox_writer import SQLiteSyncOutboxWriter

LANE_ID = "test-lane"


async def backdate_entry(db: Database, session_id: str, minutes_ago: int) -> None:
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
            FeeRule(branch_id="branch-1", name="motorbike", vehicle_type="motorbike",
                     free_minutes=0, block_minutes=60, price_per_block=5000)
        )

    yield database
    await database.dispose()


@pytest.mark.asyncio
async def test_open_shift_twice_rejected(db: Database) -> None:
    async with db.session() as session:
        use_case = OpenShiftUseCase(SQLiteShiftRepository(session))
        await use_case.execute(OpenShiftInput(branch_id="branch-1", operator_id="op-1"))

        with pytest.raises(ShiftAlreadyOpenError):
            await use_case.execute(OpenShiftInput(branch_id="branch-1", operator_id="op-1"))


@pytest.mark.asyncio
async def test_close_shift_totals_only_its_own_sessions(db: Database) -> None:
    # Open a shift
    async with db.session() as session:
        shift_id = (await OpenShiftUseCase(SQLiteShiftRepository(session)).execute(
            OpenShiftInput(branch_id="branch-1", operator_id="op-2")
        )).shift_id

    # Enter a vehicle stamped with this shift
    async with db.session() as session:
        entry = VehicleEntryUseCase(
            session_repo=SQLiteSessionRepository(session),
            vehicle_repo=SQLiteVehicleRepository(session),
            card_repo=SQLiteCardRepository(session),
            fee_rule_repo=SQLiteFeeRuleRepository(session),
            subscriber_repo=SQLiteSubscriberRepository(session),
            lane_repo=SQLiteLaneRepository(session),
            barrier=MockBarrierController(),
            outbox=SQLiteSyncOutboxWriter(session),
        )
        result = await entry.execute(
            VehicleEntryInput(lane_id=LANE_ID, plate_number="51F-99999", vehicle_type="motorbike", shift_id=shift_id)
        )
    await backdate_entry(db, result.session_id, minutes_ago=90)

    # Exit -> 2 blocks * 5000 = 10000
    async with db.session() as session:
        exit_uc = VehicleExitUseCase(
            session_repo=SQLiteSessionRepository(session),
            card_repo=SQLiteCardRepository(session),
            fee_rule_repo=SQLiteFeeRuleRepository(session),
            subscriber_repo=SQLiteSubscriberRepository(session),
            vehicle_repo=SQLiteVehicleRepository(session),
            barrier=MockBarrierController(),
            fee_calculator=FeeCalculator(),
            outbox=SQLiteSyncOutboxWriter(session),
        )
        await exit_uc.execute(VehicleExitInput(lane_id=LANE_ID, plate_number="51F-99999"))

    # Close shift — totals must reflect exactly this shift's session
    async with db.session() as session:
        close_uc = CloseShiftUseCase(SQLiteShiftRepository(session), SQLiteSessionRepository(session))
        out = await close_uc.execute(CloseShiftInput(operator_id="op-2"))

    assert out.total_sessions == 1
    assert out.total_revenue == 10000


@pytest.mark.asyncio
async def test_rfid_exit_matches_session_created_via_rfid_entry(db: Database) -> None:
    """Regression test for the fixed bug: exit-by-rfid must resolve the Card
    to its internal id before looking up the active session, matching what
    entry stored — previously it compared the raw scanned code directly and
    never found the session."""
    async with db.session() as session:
        await SQLiteCardRepository(session).create(Card(branch_id="branch-1", rfid_code="AABBCC", is_active=True))

    async with db.session() as session:
        entry = VehicleEntryUseCase(
            session_repo=SQLiteSessionRepository(session),
            vehicle_repo=SQLiteVehicleRepository(session),
            card_repo=SQLiteCardRepository(session),
            fee_rule_repo=SQLiteFeeRuleRepository(session),
            subscriber_repo=SQLiteSubscriberRepository(session),
            lane_repo=SQLiteLaneRepository(session),
            barrier=MockBarrierController(),
            outbox=SQLiteSyncOutboxWriter(session),
        )
        result = await entry.execute(VehicleEntryInput(lane_id=LANE_ID, rfid_code="AABBCC", vehicle_type="motorbike"))
    await backdate_entry(db, result.session_id, minutes_ago=30)

    async with db.session() as session:
        exit_uc = VehicleExitUseCase(
            session_repo=SQLiteSessionRepository(session),
            card_repo=SQLiteCardRepository(session),
            fee_rule_repo=SQLiteFeeRuleRepository(session),
            subscriber_repo=SQLiteSubscriberRepository(session),
            vehicle_repo=SQLiteVehicleRepository(session),
            barrier=MockBarrierController(),
            fee_calculator=FeeCalculator(),
            outbox=SQLiteSyncOutboxWriter(session),
        )
        out = await exit_uc.execute(VehicleExitInput(lane_id=LANE_ID, rfid_code="AABBCC"))

    assert out.session_id == result.session_id
    assert out.fee_amount == 5000  # 30 min -> 1 block


@pytest.mark.asyncio
async def test_create_user_and_login(db: Database) -> None:
    hasher = PBKDF2PasswordHasher()

    async with db.session() as session:
        create_uc = CreateUserUseCase(SQLiteUserRepository(session), hasher)
        await create_uc.execute(
            CreateUserInput(branch_id="branch-1", username="an.nguyen", password="s3cret!", full_name="An Nguyen")
        )

        with pytest.raises(UsernameAlreadyExistsError):
            await create_uc.execute(
                CreateUserInput(branch_id="branch-1", username="an.nguyen", password="other", full_name="Dup")
            )

    async with db.session() as session:
        login_uc = LoginUseCase(SQLiteUserRepository(session), hasher)
        out = await login_uc.execute(LoginInput(username="an.nguyen", password="s3cret!"))
        assert out.username == "an.nguyen"

        with pytest.raises(InvalidCredentialsError):
            await login_uc.execute(LoginInput(username="an.nguyen", password="wrong-password"))

        with pytest.raises(InvalidCredentialsError):
            await login_uc.execute(LoginInput(username="nobody", password="whatever"))
