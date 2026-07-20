# PMQL Bãi Xe — Project Rules for AI Agents

> Đọc file này TRƯỚC KHI sửa bất kỳ code nào.
> Mỗi tính năng có **feature map** riêng — chỉ đọc file map của tính năng cần sửa để tiết kiệm token.

---

## 1. Architecture Overview

```
Clean Architecture (4 layers — không được phá vỡ chiều phụ thuộc):

UI (PySide6)          → Application (Use Cases)  → Domain (Entities/Services)
                      ↓
             Infrastructure (SQLite/Security/Hardware)
```

**Quy tắc dependency:**
- `domain/` không import gì từ các layer khác
- `application/` chỉ import từ `domain/` và `ports/`
- `infrastructure/` implement interfaces trong `ports/`
- `ui/app.py` gọi trực tiếp async functions `_xxx(settings)` rồi dùng `asyncio.run()`

---

## 2. Key Files (luôn cần biết)

| File | Vai trò |
|------|---------|
| `src/pmql/ui/app.py` | Toàn bộ UI — 1 file duy nhất, ~1950 dòng |
| `src/pmql/ui/components.py` | `LIGHT_THEME` CSS + `modal_shell()` helper |
| `src/pmql/application/ports/repositories.py` | Tất cả interface repo (IXxxRepository) |
| `src/pmql/infrastructure/persistence/sqlite/repositories.py` | Impl SQLite của tất cả repos |
| `src/pmql/infrastructure/persistence/sqlite/models.py` | ORM models (SQLAlchemy) |
| `src/pmql/infrastructure/persistence/sqlite/database.py` | DB engine + migration inline |

---

## 3. UI Patterns (BẮT BUỘC tuân theo)

### 3.1 Icon Buttons
```python
# ĐÚNG — dùng icon_btn() helper (được định nghĩa trong launch())
edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
delete = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)

# Các style preset có sẵn:
# _BTN_EDIT_STYLE  → xanh #3b82f6
# _BTN_DEL_STYLE   → đỏ #ef4444
# _BTN_PLAIN_STYLE → xám #64748b
```

### 3.2 Tables
```python
# make_table() tự động: cột cuối = action column (fixed 160px), các cột khác stretch
table = self.make_table(["Col1", "Col2", "Thao tác"])
# Nếu cần action column rộng hơn:
table = self.make_table([...], action_col_width=210)

# Cell items phải center-align:
item = QTableWidgetItem(text)
item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
table.setItem(r, c, item)
```

### 3.3 Modals
```python
# ĐÚNG — dùng modal_shell() từ components.py
dialog, content, footer = modal_shell(self, "Tiêu đề", 620)
# content = QVBoxLayout, footer = QHBoxLayout
# Luôn thêm nút Hủy + Lưu vào footer
```

### 3.4 Async DB calls trong UI
```python
# Pattern chuẩn cho mọi async helper ở dưới launch():
async def _xxx(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SomeSQLiteRepo(session).some_method()
    finally:
        await db.dispose()

# Gọi trong UI:
result = asyncio.run(_xxx(settings))
```

### 3.5 Reload page sau CRUD
```python
# Sau khi create/update/delete, luôn dùng:
self.reload_page("fees")   # hoặc "subscribers", "cards", etc.
# KHÔNG dùng load_xxx() nếu page cần re-render hoàn toàn
```

---

## 4. Domain Enums & Constants

```python
# Card
card_type: "GUEST" | "SUBSCRIBER"
status: "AVAILABLE" | "IN_USE" | "LOST" | "LOCKED"

# Shift
status: "OPEN" | "CLOSED"

# Lane
direction: "IN" | "OUT" | "INOUT"

# FeeRule — vehicle_type codes (khớp VehicleTypeModel.code)
# Lấy danh sách từ: asyncio.run(_vehicle_name_map(settings))
# VD: "xe_may", "o_to", "xe_dap", "xe_tai"
```

---

## 5. Database Migration Rule

Mọi cột mới PHẢI thêm migration inline trong `database.py → create_all()`:
```python
# Pattern:
col_names = {col["name"] for col in (await conn.execute(text("PRAGMA table_info(table_name)"))).mappings().all()}
if "new_column" not in col_names:
    await conn.execute(text("ALTER TABLE table_name ADD COLUMN new_column TYPE DEFAULT val"))
```

---

## 6. Feature Maps

Khi AI được yêu cầu sửa một tính năng, chỉ đọc file map tương ứng:

| Tính năng | File map cần đọc |
|-----------|-----------------|
| Vận hành làn (xe vào/ra) | `.agents/maps/feature_operations.md` |
| Ca làm việc (Shift) | `.agents/maps/feature_shifts.md` |
| Thuê bao | `.agents/maps/feature_subscribers.md` |
| Thẻ RFID | `.agents/maps/feature_cards.md` |
| Biểu phí | `.agents/maps/feature_fees.md` |
| Cấu hình làn xe | `.agents/maps/feature_lanes.md` |
| Tài khoản người dùng | `.agents/maps/feature_accounts.md` |
| Tổng quan / Dashboard | `.agents/maps/feature_overview.md` |
| Thêm entity mới | `.agents/maps/guide_new_entity.md` |

---

## 7. Quick Checklist khi sửa UI

- [ ] Dùng `icon_btn()` thay vì `QPushButton` thuần
- [ ] Cell items có `setTextAlignment(Qt.AlignmentFlag.AlignCenter)`
- [ ] Modal dùng `modal_shell()` từ `components.py`
- [ ] Sau CRUD gọi `self.reload_page(key)`
- [ ] DB helper async `_xxx(settings)` đặt ngoài `launch()`, sau class `Main`
- [ ] Cột mới = migration trong `database.py`
