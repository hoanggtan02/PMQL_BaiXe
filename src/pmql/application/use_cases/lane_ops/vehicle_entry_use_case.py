"""Use Case: VehicleEntryUseCase — record vehicle entry at a lane."""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime

from pmql.application.ports.repositories import (
    ICardRepository,
    IFeeRuleRepository,
    ILaneRepository,
    ISessionRepository,
    ISubscriberRepository,
    IVehicleRepository,
)
from pmql.application.ports.hardware_ports import IBarrierController
from pmql.application.ports.sync_port import ISyncOutboxWriter
from pmql.domain.entities.session import ParkingSession
from pmql.domain.entities.vehicle import Vehicle
from pmql.domain.exceptions import (
    CardNotActiveError,
    CardNotFoundError,
    LaneNotFoundError,
    VehicleAlreadyInsideError,
)

log = structlog.get_logger(__name__)


@dataclass
class VehicleEntryInput:
    lane_id: str
    rfid_code: str | None = None        # from card reader (optional)
    plate_number: str | None = None     # from ANPR or manual input
    vehicle_type: str = "motorbike"
    operator_id: str = ""
    # Added: the operator's currently OPEN shift, if any. Stamped onto the
    # session so CloseShiftUseCase can later total up this shift's sessions.
    # Callers that don't track shifts yet can simply omit it.
    shift_id: str | None = None


@dataclass
class VehicleEntryOutput:
    session_id: str
    plate_number: str
    subscriber_id: str | None
    barrier_opened: bool
    message: str = ""


class VehicleEntryUseCase:
    """Record vehicle entry, open barrier, write outbox record atomically."""

    def __init__(
        self,
        session_repo: ISessionRepository,
        vehicle_repo: IVehicleRepository,
        card_repo: ICardRepository,
        fee_rule_repo: IFeeRuleRepository,
        subscriber_repo: ISubscriberRepository,
        lane_repo: ILaneRepository,
        barrier: IBarrierController,
        outbox: ISyncOutboxWriter,
    ) -> None:
        self._sessions = session_repo
        self._vehicles = vehicle_repo
        self._cards = card_repo
        self._fee_rules = fee_rule_repo
        self._subscribers = subscriber_repo
        self._lanes = lane_repo
        self._barrier = barrier
        self._outbox = outbox

    async def execute(self, inp: VehicleEntryInput) -> VehicleEntryOutput:
        log.info("vehicle_entry.start", lane_id=inp.lane_id, rfid=inp.rfid_code, plate=inp.plate_number)

        # 1. Validate lane
        lane = await self._lanes.get_by_id(inp.lane_id)
        if lane is None:
            raise LaneNotFoundError(inp.lane_id)

        # 2. Resolve RFID card → subscriber
        subscriber_id: str | None = None
        rfid_card_id: str | None = None
        resolved_vehicle_type = inp.vehicle_type

        if inp.rfid_code:
            card = await self._cards.get_by_rfid_code(inp.rfid_code)
            if card is None:
                raise CardNotFoundError(inp.rfid_code)
            if not card.is_active:
                raise CardNotActiveError(inp.rfid_code)
            rfid_card_id = card.id
            if card.subscriber_id:
                subscriber = await self._subscribers.get_by_id(card.subscriber_id)
                if subscriber and subscriber.is_valid_today:
                    subscriber_id = subscriber.id
                    resolved_vehicle_type = subscriber.vehicle_type

        # 3. Resolve plate number
        plate = inp.plate_number or ""

        # 4. Reject a second entry for a vehicle that never checked out.
        if plate:
            existing = await self._sessions.get_active_by_plate(plate)
            if existing is not None:
                raise VehicleAlreadyInsideError(plate)
        if rfid_card_id:
            existing_by_card = await self._sessions.get_active_by_rfid(rfid_card_id)
            if existing_by_card is not None:
                raise VehicleAlreadyInsideError(rfid_card_id)

        # 5. Find or create the Vehicle record so session.vehicle_id is
        #    always populated.
        vehicle_id: str | None = None
        if plate:
            vehicle = await self._vehicles.get_by_plate(plate)
            if vehicle is None:
                vehicle = Vehicle(
                    branch_id=lane.branch_id,
                    plate_number=plate,
                    vehicle_type=resolved_vehicle_type,
                    rfid_tag=inp.rfid_code,
                    subscriber_id=subscriber_id,
                )
                await self._vehicles.create(vehicle)
            vehicle_id = vehicle.id

        # 6. Create session (write to local SQLite first — outbox in same tx)
        session = ParkingSession(
            branch_id=lane.branch_id,
            lane_in_id=inp.lane_id,
            vehicle_id=vehicle_id,
            plate_number=plate,
            rfid_card_id=rfid_card_id,
            subscriber_id=subscriber_id,
            shift_id=inp.shift_id,
            entry_time=datetime.utcnow(),
            status="ACTIVE",
        )

        await self._sessions.create(session)

        # Outbox write — same transaction guaranteed by repository implementation
        await self._outbox.enqueue(
            entity_table="sessions",
            entity_id=session.id,
            operation="INSERT",
            payload=self._session_to_dict(session),
        )

        # 7. Open barrier
        barrier_opened = False
        try:
            await self._barrier.open()
            barrier_opened = True
        except Exception as exc:
            log.warning("vehicle_entry.barrier_open_failed", error=str(exc))
            # Don't fail the use case — session is recorded, operator can open manually

        log.info("vehicle_entry.done", session_id=session.id, barrier=barrier_opened)
        return VehicleEntryOutput(
            session_id=session.id,
            plate_number=plate,
            subscriber_id=subscriber_id,
            barrier_opened=barrier_opened,
        )

    @staticmethod
    def _session_to_dict(s: ParkingSession) -> dict[str, object]:
        return {
            "id": s.id,
            "branch_id": s.branch_id,
            "lane_in_id": s.lane_in_id,
            "vehicle_id": s.vehicle_id,
            "plate_number": s.plate_number,
            "rfid_card_id": s.rfid_card_id,
            "subscriber_id": s.subscriber_id,
            "shift_id": s.shift_id,
            "entry_time": s.entry_time.isoformat(),
            "fee_amount": s.fee_amount,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "sync_version": s.sync_version,
        }
