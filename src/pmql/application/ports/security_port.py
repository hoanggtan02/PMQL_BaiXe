"""Application Port: IPasswordHasher.

Use cases depend only on this interface — never on a concrete hashing
algorithm — so the infrastructure layer can swap implementations
(e.g. PBKDF2 now, bcrypt/argon2 later) without touching use case code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Return a salted, algorithm-tagged hash safe to store in User.password_hash."""
        ...

    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Return True if plain_password matches the stored hash."""
        ...
