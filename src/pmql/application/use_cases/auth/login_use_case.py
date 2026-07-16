"""Use Case: LoginUseCase — authenticate an operator by username/password."""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime

from pmql.application.ports.repositories import IUserRepository
from pmql.application.ports.security_port import IPasswordHasher, ITokenService
from pmql.domain.exceptions import InvalidCredentialsError

log = structlog.get_logger(__name__)

# A syntactically-valid-but-unmatchable hash used to keep verify() timing
# similar whether or not the username exists, so failed logins don't leak
# via response latency which usernames are registered.
_DUMMY_HASH = "pbkdf2_sha256$1$00$00"


@dataclass
class LoginInput:
    username: str
    password: str


@dataclass
class LoginOutput:
    user_id: str
    username: str
    role: str
    full_name: str
    access_token: str | None = None
    token_expires_at: datetime | None = None


class LoginUseCase:
    def __init__(self, user_repo: IUserRepository, password_hasher: IPasswordHasher,
                 token_service: ITokenService | None = None) -> None:
        self._users = user_repo
        self._hasher = password_hasher
        self._tokens = token_service

    async def execute(self, inp: LoginInput) -> LoginOutput:
        user = await self._users.get_by_username(inp.username)

        password_hash = user.password_hash if user else _DUMMY_HASH
        valid = self._hasher.verify(inp.password, password_hash)

        if user is None or not user.is_active or not valid:
            log.warning("login.failed", username=inp.username)
            raise InvalidCredentialsError(inp.username)

        user.last_login_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.sync_version += 1
        await self._users.update(user)

        log.info("login.success", user_id=user.id, username=user.username)
        token: str | None = None
        expires_at: datetime | None = None
        if self._tokens is not None:
            token, claims = self._tokens.issue(
                user_id=user.id, username=user.username, role=user.role, branch_id=user.branch_id
            )
            expires_at = claims.expires_at
        return LoginOutput(user.id, user.username, user.role, user.full_name, token, expires_at)
