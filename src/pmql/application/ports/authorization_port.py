"""Ports for configurable role-based access control."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RoleRecord:
    id: str
    name: str
    description: str
    permission_codes: frozenset[str]
    is_system: bool = False


class IAuthorizationRepository(ABC):
    @abstractmethod
    async def list_roles(self) -> list[RoleRecord]: ...
    @abstractmethod
    async def save_role(self, name: str, description: str, permission_codes: set[str]) -> RoleRecord: ...
    @abstractmethod
    async def list_permissions(self) -> list[tuple[str, str]]: ...
    @abstractmethod
    async def has_permission(self, role_name: str, permission_code: str) -> bool: ...
