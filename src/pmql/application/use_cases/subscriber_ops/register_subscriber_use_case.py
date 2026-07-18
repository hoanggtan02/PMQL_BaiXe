"""Use Case: RegisterSubscriberUseCase — create a monthly-pass subscriber
and, optionally, issue their first RFID card in the same step.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import date

from pmql.application.ports.repositories import ICardRepository, ISubscriberRepository, IVehicleRepository
from pmql.domain.entities.card import Card
from pmql.domain.entities.subscriber import Subscriber
from pmql.domain.entities.vehicle import Vehicle

log = structlog.get_logger(__name__)


@dataclass
class RegisterSubscriberInput:
    branch_id: str
    full_name: str
    phone: str
    identity_card: str
    vehicles: list[dict[str, str]]
    valid_from: date
    valid_until: date
    email: str | None = None
    rfid_code: str | None = None  # if provided, a Card is issued/re-linked immediately


@dataclass
class RegisterSubscriberOutput:
    subscriber_id: str
    card_id: str | None


class RegisterSubscriberUseCase:
    def __init__(self, subscriber_repo: ISubscriberRepository, card_repo: ICardRepository, vehicle_repo: IVehicleRepository) -> None:
        self._subscribers = subscriber_repo
        self._cards = card_repo
        self._vehicles = vehicle_repo

    async def execute(self, inp: RegisterSubscriberInput) -> RegisterSubscriberOutput:
        subscriber = Subscriber(
            branch_id=inp.branch_id,
            full_name=inp.full_name,
            phone=inp.phone,
            email=inp.email,
            identity_card=inp.identity_card,
            valid_from=inp.valid_from,
            valid_until=inp.valid_until,
            is_active=True,
        )
        await self._subscribers.create(subscriber)

        for v_data in inp.vehicles:
            vehicle = Vehicle(
                branch_id=inp.branch_id,
                plate_number=v_data["plate_number"],
                vehicle_type=v_data["vehicle_type"],
                subscriber_id=subscriber.id
            )
            await self._vehicles.create(vehicle)

        card_id: str | None = None
        if inp.rfid_code:
            existing = await self._cards.get_by_rfid_code(inp.rfid_code)
            if existing is not None:
                # Cards are physical objects that get reassigned — re-link
                # rather than fail on a code that already exists.
                existing.subscriber_id = subscriber.id
                existing.is_active = True
                await self._cards.update(existing)
                card_id = existing.id
            else:
                card = Card(branch_id=inp.branch_id, rfid_code=inp.rfid_code, subscriber_id=subscriber.id)
                await self._cards.create(card)
                card_id = card.id

        log.info("subscriber.registered", subscriber_id=subscriber.id, card_id=card_id)
        return RegisterSubscriberOutput(subscriber_id=subscriber.id, card_id=card_id)
