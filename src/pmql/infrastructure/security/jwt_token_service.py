"""Small dependency-free HS256 JWT adapter for local desktop sessions."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from pmql.application.ports.security_port import ITokenService, TokenClaims
from pmql.domain.exceptions import InvalidCredentialsError


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class JwtTokenService(ITokenService):
    """Create signed JWTs with only identity and expiry claims.

    Tokens are held in memory by the desktop UI, never written to SQLite.
    Signing is intentionally standard-library-only to preserve the project's
    low-dependency local-first setup.
    """

    def __init__(self, secret_key: str, expire_minutes: int = 480) -> None:
        if not secret_key or secret_key == "CHANGE_ME_RANDOM_64_CHARS":
            raise ValueError("SECRET_KEY must be changed before issuing JWTs")
        self._key = secret_key.encode("utf-8")
        self._expiry = timedelta(minutes=expire_minutes)

    def issue(self, *, user_id: str, username: str, role: str, branch_id: str) -> tuple[str, TokenClaims]:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires_at = now + self._expiry
        payload = {"sub": user_id, "username": username, "role": role, "branch_id": branch_id,
                   "iat": int(now.timestamp()), "exp": int(expires_at.timestamp())}
        header = {"alg": "HS256", "typ": "JWT"}
        encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
        encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = hmac.new(self._key, f"{encoded_header}.{encoded_payload}".encode(), hashlib.sha256).digest()
        token = f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"
        return token, TokenClaims(user_id, username, role, branch_id, expires_at)

    def verify(self, token: str) -> TokenClaims:
        try:
            header, payload, signature = token.split(".")
            expected = hmac.new(self._key, f"{header}.{payload}".encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64decode(signature)):
                raise ValueError("signature")
            decoded = json.loads(_b64decode(payload))
            expires_at = datetime.fromtimestamp(int(decoded["exp"]), tz=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                raise ValueError("expired")
            return TokenClaims(str(decoded["sub"]), str(decoded["username"]), str(decoded["role"]),
                               str(decoded["branch_id"]), expires_at)
        except (KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidCredentialsError("Invalid or expired access token") from exc
