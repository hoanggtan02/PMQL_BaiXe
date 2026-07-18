"""Authorization primitives shared by UI, CLI adapters and application facades."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Awaitable, Callable, ParamSpec, TypeVar

from pmql.application.ports.security_port import TokenClaims
from pmql.domain.exceptions import InsufficientPermissionsError

P = ParamSpec("P")
T = TypeVar("T")

ROLE_OPERATOR = "OPERATOR"
ROLE_SUPERVISOR = "SUPERVISOR"
ROLE_ADMIN = "ADMIN"


@dataclass(frozen=True)
class AuthenticatedUser:
    """The currently authenticated user, safe to hand to a UI/controller."""

    user_id: str
    username: str
    full_name: str
    role: str
    branch_id: str

    @classmethod
    def from_claims(cls, claims: TokenClaims, full_name: str) -> "AuthenticatedUser":
        return cls(claims.user_id, claims.username, full_name, claims.role, claims.branch_id)


def require_roles(*allowed_roles: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Require an ``actor=AuthenticatedUser`` argument on an async handler.

    Keeping this at the boundary means core use cases stay reusable for batch
    jobs while every UI/API action can be protected consistently.
    """
    allowed = frozenset(allowed_roles)
    if not allowed:
        raise ValueError("Authorization policy must declare at least one role")

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            actor = kwargs.get("actor")
            if not isinstance(actor, AuthenticatedUser) or actor.role not in allowed:
                raise InsufficientPermissionsError(
                    f"Required role: {', '.join(sorted(allowed))}"
                )
            return await func(*args, **kwargs)
        return wrapped
    return decorator
