# Guide: Thêm Entity mới

## Checklist đầy đủ khi thêm một entity mới (VD: Receipt, Discount...)

### 1. Domain Entity
```
src/pmql/domain/entities/receipt.py
```
```python
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

@dataclass
class Receipt:
    id: str = field(default_factory=lambda: str(uuid4()))
    branch_id: str = ""
    # ... fields
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    sync_version: int = 1
```

### 2. ORM Model
```
src/pmql/infrastructure/persistence/sqlite/models.py
```
Thêm class `ReceiptModel(Base)` với `__tablename__ = "receipts"`.

### 3. Database Migration
```
src/pmql/infrastructure/persistence/sqlite/database.py → create_all()
```
```python
# Pattern thêm cột vào bảng đã tồn tại:
receipt_cols = (await conn.execute(text("PRAGMA table_info(receipts)"))).mappings().all()
if receipt_cols:
    col_names = {c["name"] for c in receipt_cols}
    if "new_field" not in col_names:
        await conn.execute(text("ALTER TABLE receipts ADD COLUMN new_field TYPE DEFAULT val"))
# Bảng mới sẽ tự được tạo bởi Base.metadata.create_all()
```

### 4. Repository Interface
```
src/pmql/application/ports/repositories.py
```
```python
class IReceiptRepository(ABC):
    @abstractmethod
    async def create(self, receipt: Receipt) -> None: ...
    @abstractmethod
    async def get_by_id(self, receipt_id: str) -> Receipt | None: ...
    @abstractmethod
    async def list_all(self) -> list[Receipt]: ...
```

### 5. Repository Implementation
```
src/pmql/infrastructure/persistence/sqlite/repositories.py
```
```python
class SQLiteReceiptRepository(IReceiptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: ReceiptModel) -> Receipt:
        return Receipt(id=m.id, ...)

    async def create(self, receipt: Receipt) -> None:
        self._session.add(ReceiptModel(id=receipt.id, ...))

    async def get_by_id(self, rid: str) -> Receipt | None:
        m = await self._session.get(ReceiptModel, rid)
        return self._to_entity(m) if m else None

    async def list_all(self) -> list[Receipt]:
        result = await self._session.execute(select(ReceiptModel))
        return [self._to_entity(r) for r in result.scalars()]
```

### 6. Use Case (nếu cần)
```
src/pmql/application/use_cases/management_ops.py
```
Hoặc tạo file mới trong `use_cases/receipt_ops/`.

### 7. UI Async Helpers (cuối file app.py, sau class Main)
```python
async def _receipts(settings: Settings) -> list[Receipt]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteReceiptRepository(session).list_all()
    finally:
        await db.dispose()
```

### 8. UI Page (trong class Main, trong launch())
```python
def receipt_page(self) -> QWidget:
    page, box = self.page()
    # ... header, table, etc.
    self.receipt_table = self.make_table(["Cột 1", "Cột 2", "Thao tác"])
    box.addWidget(self.receipt_table, 1)
    self.load_receipts()
    return page

def load_receipts(self) -> None:
    if not hasattr(self, "receipt_table"): return
    try: items = asyncio.run(_receipts(settings))
    except Exception: return
    self.receipt_table.setRowCount(len(items))
    for r, item in enumerate(items):
        # ... set cells
        edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
        # ...
```

### 9. Đăng ký page trong page_factories
```python
# Trong Main.__init__():
self.page_factories = {
    ...,
    "receipts": self.receipt_page,  # ← thêm vào đây
}
```

### 10. Thêm nav button trong sidebar
```python
# Trong build_sidebar():
groups = [
    ("QUẢN LÝ", [
        ...,
        ("receipts", "🧾  Hóa đơn"),  # ← thêm vào đây
    ]),
]
```

### 11. Cập nhật breadcrumb
```python
# Trong go():
{..., "receipts": "Quản lý hóa đơn"}
```

### 12. Thêm permission code (nếu cần phân quyền)
```python
# Trong build_sidebar():
required = {..., "receipts": "receipt.manage"}

# Trong SQLiteAuthorizationRepository - thêm permission mới
```
