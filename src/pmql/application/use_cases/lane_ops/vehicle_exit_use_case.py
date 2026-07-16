"""Use Case: VehicleExitUseCase — calculate fee, close session, open barrier."""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime

from pmql.application.ports.hardware_ports import IBarrierController
from pmql.application.ports.repositories import (
    ICardRepository,
    IFeeRuleRepository,
    ISessionRepository,
    ISubscriberRepository,
    IVehicleRepository,
)
from pmql.application.ports.sync_port import ISyncOutboxWriter
from pmql.domain.entities.session import ParkingSession
from pmql.domain.exceptions import (
    FeeRuleNotFoundError,
    SessionAlreadyClosedError,
    SessionNotFoundError,
)
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.domain.value_objects.money import Money

log = structlog.get_logger(__name__)


@dataclass
class VehicleExitInput:
    lane_id: str
    rfid_code: str | None = None
    plate_number: str | None = None
    operator_id: str = ""


@dataclass
class VehicleExitOutput:
    session_id: str
    plate_number: str
    fee_amount: int          # VND
    is_subscriber: bool
    barrier_opened: bool
    duration_minutes: int
    message: str = ""


class VehicleExitUseCase:
    """Calculate fee, close session, enqueue outbox, open barrier."""

    def __init__(
        self,
        session_repo: ISessionRepository,
        card_repo: ICardRepository,
        fee_rule_repo: IFeeRuleRepository,
        subscriber_repo: ISubscriberRepository,
        vehicle_repo: IVehicleRepository,
        barrier: IBarrierController,
        fee_calculator: FeeCalculator,
        outbox: ISyncOutboxWriter,
    ) -> None:
        self._sessions = session_repo
        self._cards = card_repo
        self._fee_rules = fee_rule_repo
        self._subscribers = subscriber_repo
        self._vehicles = vehicle_repo
        self._barrier = barrier
        self._calculator = fee_calculator
        self._outbox = outbox

    async def execute(self, inp: VehicleExitInput) -> VehicleExitOutput:
        log.info("vehicle_exit.start", lane_id=inp.lane_id, rfid=inp.rfid_code, plate=inp.plate_number)

        # 1. Locate active session.
        #
        # BUGFIX: `ParkingSession.rfid_card_id` stores the *Card entity's
        # internal id* (see VehicleEntryUseCase — it sets
        # `rfid_card_id = card.id`), not the raw scanned RFID code. The
        # previous version called `get_active_by_rfid(inp.rfid_code)` with
        # the raw scanned code directly, which never matched the stored
        # card id — so a vehicle that entered via RFID could never be
        # found by RFID on exit (only by plate, if provided). We now
        # resolve the Card first, exactly as entry does.
        session: ParkingSession | None = None
        card = None

        if inp.rfid_code:
            card = await self._cards.get_by_rfid_code(inp.rfid_code)
            if card is not None:
                session = await self._sessions.get_active_by_rfid(card.id)

        if session is None and inp.plate_number:
            session = await self._sessions.get_active_by_plate(inp.plate_number)

        if session is None:
            raise SessionNotFoundError(f"rfid={inp.rfid_code}, plate={inp.plate_number}")

        if session.status == "CLOSED":
            raise SessionAlreadyClosedError(session.id)

        # 2. Determine fee
        exit_time = datetime.utcnow()
        fee = Money.zero()
        is_subscriber = False

        if session.subscriber_id:
            subscriber = await self._subscribers.get_by_id(session.subscriber_id)
            if subscriber and subscriber.is_valid_today:
                is_subscriber = True
                fee = Money.zero()  # subscriber pass — no charge

        if not is_subscriber:
            # Resolve the real vehicle_type. Priority:
            #  1. Vehicle record matched by plate number (most reliable).
            #  2. Vehicle record matched by the RFID card's linked vehicle_id.
            #  3. Fallback to 'motorbike' — logged as a warning since billing
            #     a car/truck at the motorbike rate would undercharge them.
            vehicle_type: str | None = None

            vehicle = await self._vehicles.get_by_plate(session.plate_number) if session.plate_number else None

            if vehicle is None and session.rfid_card_id:
                # Reuse the card resolved in step 1 when possible; otherwise
                # (e.g. exit was matched by plate only) look it up by its id.
                if card is None:
                    card = await self._cards.get_by_id(session.rfid_card_id)
                if card and card.vehicle_id:
                    vehicle = await self._vehicles.get_by_id(card.vehicle_id)

            if vehicle is not None:
                vehicle_type = vehicle.vehicle_type

            if not vehicle_type:
                vehicle_type = "motorbike"
                log.warning(
                    "vehicle_exit.vehicle_type_unresolved",
                    session_id=session.id,
                    plate=session.plate_number,
                    fallback="motorbike",
                )

            fee_rule = await self._fee_rules.get_active_by_vehicle_type(vehicle_type)
            if fee_rule is None:
                raise FeeRuleNotFoundError(f"No active rule for vehicle_type={vehicle_type}")

            fee = self._calculator.calculate(
                entry=session.entry_time,
                exit_=exit_time,
                rule=fee_rule,
            )

        # 3. Close session
        session.close(
            exit_time=exit_time,
            fee_amount=fee.amount,
            lane_out_id=inp.lane_id,
        )
        await self._sessions.update(session)

        # Outbox — same transaction as update
        await self._outbox.enqueue(
            entity_table="sessions",
            entity_id=session.id,
            operation="UPDATE",
            payload=self._session_to_dict(session),
        )

        # 4. Open barrier
        barrier_opened = False
        try:
            await self._barrier.open()
            barrier_opened = True
        except Exception as exc:
            log.warning("vehicle_exit.barrier_failed", error=str(exc))

        duration_minutes = int((exit_time - session.entry_time).total_seconds() // 60)
        log.info("vehicle_exit.done", session_id=session.id, fee=fee.amount, duration=duration_minutes)

        return VehicleExitOutput(
            session_id=session.id,
            plate_number=session.plate_number,
            fee_amount=fee.amount,
            is_subscriber=is_subscriber,
            barrier_opened=barrier_opened,
            duration_minutes=duration_minutes,
        )

    @staticmethod
    def _session_to_dict(s: ParkingSession) -> dict[str, object]:
        return {
            "id": s.id,
            "branch_id": s.branch_id,
            "lane_in_id": s.lane_in_id,
            "lane_out_id": s.lane_out_id,
            "plate_number": s.plate_number,
            "rfid_card_id": s.rfid_card_id,
            "subscriber_id": s.subscriber_id,
            "shift_id": s.shift_id,
            "entry_time": s.entry_time.isoformat(),
            "exit_time": s.exit_time.isoformat() if s.exit_time else None,
            "fee_amount": s.fee_amount,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "sync_version": s.sync_version,
        }
