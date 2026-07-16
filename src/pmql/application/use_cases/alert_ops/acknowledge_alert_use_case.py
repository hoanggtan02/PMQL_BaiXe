"""Use Case: AcknowledgeAlertUseCase — operator acknowledges a system alert."""

from __future__ import annotations

import structlog
from dataclasses import dataclass

from pmql.application.ports.repositories import IAlertRepository
from pmql.domain.exceptions import AlertNotFoundError

log = structlog.get_logger(__name__)


@dataclass
class AcknowledgeAlertInput:
    alert_id: str
    user_id: str


class AcknowledgeAlertUseCase:
    def __init__(self, alert_repo: IAlertRepository) -> None:
        self._alerts = alert_repo

    async def execute(self, inp: AcknowledgeAlertInput) -> None:
        alert = await self._alerts.get_by_id(inp.alert_id)
        if alert is None:
            raise AlertNotFoundError(inp.alert_id)

        alert.acknowledge(inp.user_id)
        await self._alerts.update(alert)
        log.info("alert.acknowledged", alert_id=alert.id, user_id=inp.user_id)
