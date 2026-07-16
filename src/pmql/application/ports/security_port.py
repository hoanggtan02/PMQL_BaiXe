"""Application Port: IPasswordHasher.

Use cases depend only on this interface — never on a concrete hashing
algorithm — so the infrastructure layer can swap implementations
(e.g. PBKDF2 now, bcrypt/argon2 later) without touching use case code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass


class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Return a salted, algorithm-tagged hash safe to store in User.password_hash."""
        ...

    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Return True if plain_password matches the stored hash."""
        ...


@dataclass(frozen=True)
class TokenClaims:
    """Identity carried by an authenticated access token."""

    user_id: str
    username: str
    role: str
    branch_id: str
    expires_at: datetime


class ITokenService(ABC):
    """Issues and validates short-lived access tokens.

    The application layer owns this contract; the JWT implementation belongs
    in infrastructure so it can later be replaced without changing use cases.
    """

    @abstractmethod
    def issue(self, *, user_id: str, username: str, role: str, branch_id: str) -> tuple[str, TokenClaims]:
        ...

    @abstractmethod
    def verify(self, token: str) -> TokenClaims:
        ...
