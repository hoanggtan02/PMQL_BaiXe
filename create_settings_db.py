import sys

# 1. Append to models.py
with open("src/pmql/infrastructure/persistence/sqlite/models.py", "a", encoding="utf-8") as f:
    f.write("""

class SystemSettingsModel(Base):
    __tablename__ = "system_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    parking_name: Mapped[str] = mapped_column(String(100), default="Bãi Giữ Xe PMQL")
    phone: Mapped[str] = mapped_column(String(20), default="", nullable=True)
    address: Mapped[str] = mapped_column(String(200), default="", nullable=True)
    footer_text: Mapped[str] = mapped_column(String(200), default="", nullable=True)
    
    capacity_total: Mapped[int] = mapped_column(Integer, default=0)
    capacity_moto: Mapped[int] = mapped_column(Integer, default=0)
    capacity_car: Mapped[int] = mapped_column(Integer, default=0)
    capacity_truck: Mapped[int] = mapped_column(Integer, default=0)
    
    auto_barrier_delay_sec: Mapped[int] = mapped_column(Integer, default=8)
    free_time_mins: Mapped[int] = mapped_column(Integer, default=5)
    anpr_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    night_surcharge_from: Mapped[str] = mapped_column(String(10), default="22:00")
    night_surcharge_to: Mapped[str] = mapped_column(String(10), default="06:00")
    tcp_port: Mapped[int] = mapped_column(Integer, default=9001)
    
    bank_name: Mapped[str] = mapped_column(String(100), default="", nullable=True)
    bank_account_number: Mapped[str] = mapped_column(String(50), default="", nullable=True)
    bank_account_name: Mapped[str] = mapped_column(String(100), default="", nullable=True)
    
    alert_email: Mapped[str] = mapped_column(String(100), default="", nullable=True)
""")

# 2. Append to repositories.py
with open("src/pmql/infrastructure/persistence/sqlite/repositories.py", "a", encoding="utf-8") as f:
    f.write("""

class SQLiteSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_settings(self):
        from pmql.infrastructure.persistence.sqlite.models import SystemSettingsModel
        from sqlalchemy import select
        result = await self._session.execute(select(SystemSettingsModel).where(SystemSettingsModel.id == "default"))
        row = result.scalars().first()
        if not row:
            row = SystemSettingsModel(id="default")
            self._session.add(row)
            await self._session.flush()
        return row

    async def save_settings(self, data: dict) -> None:
        row = await self.get_settings()
        for k, v in data.items():
            if hasattr(row, k):
                setattr(row, k, v)
        await self._session.flush()
""")

print("Appended models and repositories")
