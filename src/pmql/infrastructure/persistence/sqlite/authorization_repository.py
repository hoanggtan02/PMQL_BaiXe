"""SQLite implementation of dynamic roles and permissions."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pmql.application.ports.authorization_port import RoleRecord
from pmql.infrastructure.persistence.sqlite.models import PermissionModel, RoleModel, RolePermissionModel


DEFAULT_PERMISSIONS = {
    "lane.view": "Xem làn xe",
    "lane.add": "Thêm làn xe",
    "lane.edit": "Sửa làn xe",
    "lane.delete": "Xóa làn xe",
    "lane.operate": "Ghi nhận xe vào/ra",
    "session.view": "Xem phiên gửi xe",
    "shift.view": "Xem ca làm việc",
    "shift.manage": "Mở và đóng ca làm việc",
    "subscriber.view": "Xem danh sách thuê bao",
    "subscriber.add": "Thêm thuê bao",
    "subscriber.edit": "Sửa thuê bao",
    "subscriber.delete": "Xóa thuê bao",
    "card.view": "Xem danh sách thẻ",
    "card.add": "Thêm thẻ RFID",
    "card.edit": "Sửa thẻ RFID",
    "card.delete": "Xóa thẻ RFID",
    "fee.view": "Xem cấu hình biểu phí",
    "fee.add": "Thêm biểu phí/loại xe",
    "fee.edit": "Sửa biểu phí/loại xe",
    "fee.delete": "Xóa biểu phí/loại xe",
    "device.view": "Xem danh sách thiết bị",
    "device.add": "Thêm thiết bị",
    "device.edit": "Sửa thiết bị",
    "device.delete": "Xóa thiết bị",
    "alert.view": "Xem danh sách cảnh báo",
    "alert.handle": "Xử lý cảnh báo",
    "report.view": "Xem báo cáo",
    "report.export": "Xuất báo cáo",
    "user.view": "Xem danh sách tài khoản",
    "user.add": "Thêm tài khoản",
    "user.edit": "Sửa tài khoản",
    "user.delete": "Xóa tài khoản",
    "role.manage": "Quản lý vai trò & quyền",
}


class SQLiteAuthorizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_permission_catalog(self) -> None:
        for code, description in DEFAULT_PERMISSIONS.items():
            existing = (await self._session.execute(select(PermissionModel).where(PermissionModel.code == code))).scalars().first()
            if existing is None:
                self._session.add(PermissionModel(id=str(uuid4()), code=code, description=description))
        await self._session.flush()

    async def list_permissions(self) -> list[tuple[str, str]]:
        await self.ensure_permission_catalog()
        result = await self._session.execute(select(PermissionModel).where(PermissionModel.is_deleted.is_(False)).order_by(PermissionModel.code))
        return [(permission.code, permission.description) for permission in result.scalars().all()]

    async def create_permission(self, code: str, description: str) -> tuple[str, str]:
        code, description = code.strip().lower(), description.strip()
        if not code or not description:
            raise ValueError("Mã và mô tả quyền là bắt buộc")
        existing = (await self._session.execute(select(PermissionModel).where(PermissionModel.code == code))).scalars().first()
        if existing is not None:
            if existing.is_deleted:
                existing.is_deleted, existing.description = False, description
                await self._session.flush()
                return existing.code, existing.description
            raise ValueError("Mã quyền đã tồn tại")
        self._session.add(PermissionModel(id=str(uuid4()), code=code, description=description))
        await self._session.flush()
        return code, description

    async def list_roles(self) -> list[RoleRecord]:
        await self.ensure_permission_catalog()
        roles = (await self._session.execute(select(RoleModel).where(RoleModel.is_deleted.is_(False)).order_by(RoleModel.name))).scalars().all()
        output: list[RoleRecord] = []
        for role in roles:
            ids = (await self._session.execute(select(RolePermissionModel.permission_id).where(RolePermissionModel.role_id == role.id))).scalars().all()
            codes = (await self._session.execute(select(PermissionModel.code).where(PermissionModel.id.in_(ids), PermissionModel.is_deleted.is_(False)))).scalars().all() if ids else []
            output.append(RoleRecord(role.id, role.name, role.description, frozenset(codes), role.is_system))
        return output

    async def ensure_starter_roles(self) -> None:
        """Seed editable starter roles, and ensure ADMIN always has all permissions."""
        all_codes = set(DEFAULT_PERMISSIONS)
        roles = await self.list_roles()
        if not roles:
            await self.save_role("ADMIN", "Toàn quyền quản trị", all_codes)
            
            supervisor_perms = all_codes - {
                "user.add", "user.edit", "user.delete", "role.manage",
                "device.delete", "fee.delete"
            }
            await self.save_role("SUPERVISOR", "Giám sát vận hành", supervisor_perms)
            
            operator_perms = {
                "lane.view", "lane.operate", "session.view", 
                "shift.view", "shift.manage", "alert.view", "alert.handle",
                "subscriber.view", "card.view", "fee.view"
            }
            await self.save_role("OPERATOR", "Nhân viên vận hành làn", operator_perms)
        else:
            # Ensure ADMIN always has the complete set of permissions if it exists
            admin_role = next((r for r in roles if r.name == "ADMIN"), None)
            if admin_role and admin_role.permission_codes != all_codes:
                await self.save_role("ADMIN", admin_role.description, all_codes)

    async def save_role(self, name: str, description: str, permission_codes: set[str]) -> RoleRecord:
        await self.ensure_permission_catalog()
        role = (await self._session.execute(select(RoleModel).where(RoleModel.name == name))).scalars().first()
        if role is None:
            role = RoleModel(id=str(uuid4()), name=name, description=description)
            self._session.add(role)
            await self._session.flush()
        else:
            role.description, role.is_deleted = description, False
        permissions = (await self._session.execute(select(PermissionModel).where(PermissionModel.code.in_(permission_codes), PermissionModel.is_deleted.is_(False)))).scalars().all()
        await self._session.execute(RolePermissionModel.__table__.delete().where(RolePermissionModel.role_id == role.id))
        self._session.add_all([RolePermissionModel(role_id=role.id, permission_id=permission.id) for permission in permissions])
        await self._session.flush()
        return RoleRecord(role.id, role.name, role.description, frozenset(permission.code for permission in permissions), role.is_system)

    async def has_permission(self, role_name: str, permission_code: str) -> bool:
        for role in await self.list_roles():
            if role.name == role_name:
                return permission_code in role.permission_codes
        return False
