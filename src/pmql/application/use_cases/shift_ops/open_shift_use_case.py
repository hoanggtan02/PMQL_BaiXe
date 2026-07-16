"""Use Case: OpenShiftUseCase — start an operator's work shift."""

from __future__ import annotations

import structlog
from dataclasses import dataclass

from pmql.application.ports.repositories import IShiftRepository
from pmql.domain.entities.shift import Shift
from pmql.domain.exceptions import ShiftAlreadyOpenError

log = structlog.get_logger(__name__)


@dataclass
class OpenShiftInput:
    branch_id: str
    operator_id: str


@dataclass
class OpenShiftOutput:
    shift_id: str
    start_time: str


class OpenShiftUseCase:
    """Open a new shift for an operator — rejects a second concurrent shift."""

    def __init__(self, shift_repo: IShiftRepository) -> None:
        self._shifts = shift_repo

    async def execute(self, inp: OpenShiftInput) -> OpenShiftOutput:
        existing = await self._shifts.get_open_by_operator(inp.operator_id)
        if existing is not None:
            raise ShiftAlreadyOpenError(inp.operator_id)

        shift = Shift(branch_id=inp.branch_id, operator_id=inp.operator_id, status="OPEN")
        await self._shifts.create(shift)

        log.info("shift.opened", shift_id=shift.id, operator_id=inp.operator_id)
        return OpenShiftOutput(shift_id=shift.id, start_time=shift.start_time.isoformat())
