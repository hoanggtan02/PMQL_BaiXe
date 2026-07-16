"""PBKDF2-SHA256 password hasher.

Deliberately uses only the stdlib (hashlib/secrets) so it doesn't add a
new dependency to pyproject.toml. Stored format:

    pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>

The iteration count is embedded in the stored hash so it can be raised
in the future without invalidating already-hashed passwords (old hashes
keep verifying with their original iteration count).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from pmql.application.ports.security_port import IPasswordHasher

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


class PBKDF2PasswordHasher(IPasswordHasher):
    """Stdlib-only password hasher — no bcrypt/argon2 dependency required."""

    def hash(self, plain_password: str) -> str:
        salt = secrets.token_hex(_SALT_BYTES)
        digest = self._derive(plain_password, salt, _ITERATIONS)
        return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_s, salt, digest = password_hash.split("$")
        except ValueError:
            return False
        if algorithm != _ALGORITHM:
            return False
        candidate = self._derive(plain_password, salt, int(iterations_s))
        return hmac.compare_digest(candidate, digest)

    @staticmethod
    def _derive(plain_password: str, salt: str, iterations: int) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), bytes.fromhex(salt), iterations
        ).hex()
