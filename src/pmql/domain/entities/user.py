"""Domain entity: User (system operator / admin)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class User:
    """System operator or administrator."""

    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    username: str = ""
    password_hash: str = ""
    full_name: str = ""
    role: str = "OPERATOR"      # 'OPERATOR' | 'SUPERVISOR' | 'ADMIN'
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
