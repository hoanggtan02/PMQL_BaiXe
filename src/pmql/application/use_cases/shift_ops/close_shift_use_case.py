"""Use Case: CloseShiftUseCase — close an operator's work shift and record totals."""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime

from pmql.application.ports.repositories import ISessionRepository, IShiftRepository
from pmql.domain.exceptions import ShiftNotFoundError

log = structlog.get_logger(__name__)


@dataclass
class CloseShiftInput:
    operator_id: str
    actual_ending_cash: int | None = None
    closing_notes: str | None = None


@dataclass
class CloseShiftOutput:
    shift_id: str
    total_sessions: int
    total_revenue: int
    discrepancy: int = 0


class CloseShiftUseCase:
    """Close the operator's currently open shift.

    Totals are computed from sessions linked to this shift via
    ``ParkingSession.shift_id`` — VehicleEntryUseCase stamps the active
    shift onto every new session, and SQLiteSessionRepository.list_by_shift
    filters on it (both were previously missing/stubbed).
    """

    def __init__(self, shift_repo: IShiftRepository, session_repo: ISessionRepository) -> None:
        self._shifts = shift_repo
        self._sessions = session_repo

    async def execute(self, inp: CloseShiftInput) -> CloseShiftOutput:
        shift = await self._shifts.get_open_by_operator(inp.operator_id)
        if shift is None:
            raise ShiftNotFoundError(inp.operator_id)

        sessions = await self._sessions.list_by_shift(shift.id)
        total_sessions = len(sessions)
        total_revenue = sum(s.fee_amount for s in sessions)

        shift.close(
            end_time=datetime.utcnow(), 
            total_sessions=total_sessions, 
            total_revenue=total_revenue,
            actual_ending_cash=inp.actual_ending_cash,
            closing_notes=inp.closing_notes
        )
        await self._shifts.update(shift)

        discrepancy = 0
        if inp.actual_ending_cash is not None:
            expected_cash = shift.starting_cash + total_revenue
            discrepancy = inp.actual_ending_cash - expected_cash

        log.info("shift.closed", shift_id=shift.id, total_sessions=total_sessions, total_revenue=total_revenue, discrepancy=discrepancy)
        return CloseShiftOutput(
            shift_id=shift.id, 
            total_sessions=total_sessions, 
            total_revenue=total_revenue,
            discrepancy=discrepancy
        )
