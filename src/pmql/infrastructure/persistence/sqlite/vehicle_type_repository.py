"""SQLite storage for configurable vehicle categories."""
from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pmql.infrastructure.persistence.sqlite.models import VehicleTypeModel


class SQLiteVehicleTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_defaults(self) -> None:
        for code, name in (("motorbike", "Xe máy"), ("car", "Ô tô"), ("truck", "Xe tải")):
            item = (await self._session.execute(select(VehicleTypeModel).where(VehicleTypeModel.code == code))).scalars().first()
            if item is None:
                self._session.add(VehicleTypeModel(id=str(uuid4()), code=code, display_name=name))
        await self._session.flush()

    async def list_all(self) -> list[VehicleTypeModel]:
        await self.ensure_defaults()
        result = await self._session.execute(select(VehicleTypeModel).where(VehicleTypeModel.is_deleted.is_(False)).order_by(VehicleTypeModel.display_name))
        return list(result.scalars().all())

    async def create(self, code: str, display_name: str) -> VehicleTypeModel:
        if not code.strip() or not display_name.strip():
            raise ValueError("Mã và tên loại xe là bắt buộc")
        existing = (await self._session.execute(select(VehicleTypeModel).where(VehicleTypeModel.code == code.strip().lower()))).scalars().first()
        if existing is not None:
            raise ValueError("Mã loại xe đã tồn tại")
        item = VehicleTypeModel(id=str(uuid4()), code=code.strip().lower(), display_name=display_name.strip())
        self._session.add(item); await self._session.flush(); return item

    async def update(self, item_id: str, code: str, display_name: str) -> VehicleTypeModel:
        item = await self._session.get(VehicleTypeModel, item_id)
        if item is None or item.is_deleted:
            raise ValueError("Không tìm thấy loại xe")
        code = code.strip().lower()
        if not code or not display_name.strip():
            raise ValueError("Mã và tên loại xe là bắt buộc")
        duplicate = (await self._session.execute(select(VehicleTypeModel).where(VehicleTypeModel.code == code, VehicleTypeModel.id != item_id))).scalars().first()
        if duplicate is not None:
            raise ValueError("Mã loại xe đã tồn tại")
        item.code = code
        item.display_name = display_name.strip()
        await self._session.flush()
        return item

    async def delete(self, item_id: str) -> None:
        item = await self._session.get(VehicleTypeModel, item_id)
        if item: item.is_deleted = True; await self._session.flush()
