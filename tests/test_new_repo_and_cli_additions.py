"""Tests for the gaps closed in this change, per README "Chưa có":

- `IFeeRuleRepository.delete` was missing entirely (only soft-disable via
  `update(is_active=False)` existed).
- There was no way to list parking sessions at all (`list-sessions` was
  documented in the README/CLI docstring but never implemented at any
  layer) — `ISessionRepository.list_recent` plus the `list-sessions` CLI
  command close that gap.
- The CLI (`main.py`) had no subcommands for shift/auth/subscriber/alert
  use cases even though the use cases themselves already existed.
"""

from __future__ import annotations

from datetime import date

import pytest

from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import VehicleEntryInput, VehicleEntryUseCase
from pmql.domain.entities.fee_rule import FeeRule
from pmql.domain.entities.lane import Lane
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
from pmql.main import build_parser

LANE_ID = "test-lane"
BRANCH_ID = "branch-1"


@pytest.fixture
async def db(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    await database.create_all()
    async with database.session() as session:
        await SQLiteLaneRepository(session).create(
            Lane(id=LANE_ID, branch_id=BRANCH_ID, name="Test Lane", direction="BIDIRECTIONAL")
        )
    yield database
    await database.dispose()


@pytest.mark.asyncio
async def test_fee_rule_delete_removes_the_rule(db: Database) -> None:
    async with db.session() as session:
        repo = SQLiteFeeRuleRepository(session)
        rule = FeeRule(branch_id=BRANCH_ID, name="tam", vehicle_type="truck", price_per_block=30000)
        await repo.create(rule)
        assert await repo.get_by_id(rule.id) is not None

        await repo.delete(rule.id)
        assert await repo.get_by_id(rule.id) is None

        # Deleting an id that doesn't exist is a no-op, not an error.
        await repo.delete("does-not-exist")


@pytest.mark.asyncio
async def test_session_list_recent_scopes_to_branch_and_orders_newest_first(db: Database) -> None:
    async with db.session() as session:
        await SQLiteFeeRuleRepository(session).create(
            FeeRule(branch_id=BRANCH_ID, vehicle_type="motorbike", price_per_block=5000)
        )

    async def enter(plate: str) -> str:
        async with db.session() as session:
            uc = VehicleEntryUseCase(
                session_repo=SQLiteSessionRepository(session),
                vehicle_repo=SQLiteVehicleRepository(session),
                card_repo=SQLiteCardRepository(session),
                fee_rule_repo=SQLiteFeeRuleRepository(session),
                subscriber_repo=SQLiteSubscriberRepository(session),
                lane_repo=SQLiteLaneRepository(session),
                barrier=MockBarrierController(),
                outbox=SQLiteSyncOutboxWriter(session),
            )
            out = await uc.execute(VehicleEntryInput(lane_id=LANE_ID, plate_number=plate, vehicle_type="motorbike"))
            return out.session_id

    first_id = await enter("51F-00001")
    second_id = await enter("51F-00002")

    async with db.session() as session:
        recent = await SQLiteSessionRepository(session).list_recent(BRANCH_ID, limit=10)

    ids = [s.id for s in recent]
    assert first_id in ids and second_id in ids
    # Newest entry first.
    assert ids.index(second_id) < ids.index(first_id)

    async with db.session() as session:
        scoped_out = await SQLiteSessionRepository(session).list_recent("some-other-branch", limit=10)
    assert scoped_out == []


def test_cli_registers_all_use_case_commands() -> None:
    """Every use case that existed at the application layer before this
    change (shift open/close, login, create-user, register-subscriber,
    ack-alert) now has a matching subcommand, plus `list-sessions`."""
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices  # type: ignore[union-attr]

    for expected in (
        "init-db", "enter", "exit", "list-sessions", "create-user",
        "login", "open-shift", "close-shift", "register-subscriber", "ack-alert",
    ):
        assert expected in choices, f"CLI command '{expected}' is not registered"
