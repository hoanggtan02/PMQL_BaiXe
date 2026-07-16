from __future__ import annotations

from datetime import timedelta

import pytest

from pmql.application.security import AuthenticatedUser, ROLE_ADMIN, ROLE_OPERATOR, require_roles
from pmql.domain.exceptions import InsufficientPermissionsError, InvalidCredentialsError
from pmql.infrastructure.security.jwt_token_service import JwtTokenService


def test_jwt_round_trip_and_tamper_rejection() -> None:
    service = JwtTokenService("test-secret", expire_minutes=10)
    token, claims = service.issue(user_id="u1", username="an", role=ROLE_OPERATOR, branch_id="b1")
    assert service.verify(token) == claims
    with pytest.raises(InvalidCredentialsError):
        service.verify(token + "x")


@pytest.mark.asyncio
async def test_role_decorator_requires_an_allowed_actor() -> None:
    @require_roles(ROLE_ADMIN)
    async def admin_action(*, actor: AuthenticatedUser) -> str:
        return "ok"

    operator = AuthenticatedUser("u1", "an", "An", ROLE_OPERATOR, "b1")
    with pytest.raises(InsufficientPermissionsError):
        await admin_action(actor=operator)
    admin = AuthenticatedUser("u2", "admin", "Admin", ROLE_ADMIN, "b1")
    assert await admin_action(actor=admin) == "ok"
