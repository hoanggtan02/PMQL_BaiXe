"""Resolve the active user from an access token."""

from __future__ import annotations

from pmql.application.ports.repositories import IUserRepository
from pmql.application.ports.security_port import ITokenService
from pmql.application.security import AuthenticatedUser
from pmql.domain.exceptions import InvalidCredentialsError


class GetCurrentUserUseCase:
    def __init__(self, user_repo: IUserRepository, token_service: ITokenService) -> None:
        self._users = user_repo
        self._tokens = token_service

    async def execute(self, access_token: str) -> AuthenticatedUser:
        claims = self._tokens.verify(access_token)
        user = await self._users.get_by_id(claims.user_id)
        if (
            user is None
            or not user.is_active
            or user.role != claims.role
            or user.branch_id != claims.branch_id
        ):
            raise InvalidCredentialsError("Session is no longer valid")
        return AuthenticatedUser.from_claims(claims, user.full_name)
