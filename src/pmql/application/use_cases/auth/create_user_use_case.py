"""Use Case: CreateUserUseCase — provision a new operator/admin account."""

from __future__ import annotations

import structlog
from dataclasses import dataclass

from pmql.application.ports.repositories import IUserRepository
from pmql.application.ports.security_port import IPasswordHasher
from pmql.application.security import VALID_ROLES
from pmql.domain.entities.user import User
from pmql.domain.exceptions import InvalidRoleError, UsernameAlreadyExistsError

log = structlog.get_logger(__name__)


@dataclass
class CreateUserInput:
    branch_id: str
    username: str
    password: str
    full_name: str
    role: str = "OPERATOR"  # 'OPERATOR' | 'SUPERVISOR' | 'ADMIN'


@dataclass
class CreateUserOutput:
    user_id: str


class CreateUserUseCase:
    def __init__(self, user_repo: IUserRepository, password_hasher: IPasswordHasher) -> None:
        self._users = user_repo
        self._hasher = password_hasher

    async def execute(self, inp: CreateUserInput) -> CreateUserOutput:
        if inp.role not in VALID_ROLES:
            raise InvalidRoleError(inp.role)
        if await self._users.get_by_username(inp.username) is not None:
            raise UsernameAlreadyExistsError(inp.username)

        user = User(
            branch_id=inp.branch_id,
            username=inp.username,
            password_hash=self._hasher.hash(inp.password),
            full_name=inp.full_name,
            role=inp.role,
        )
        await self._users.create(user)

        log.info("user.created", user_id=user.id, username=user.username, role=user.role)
        return CreateUserOutput(user_id=user.id)
