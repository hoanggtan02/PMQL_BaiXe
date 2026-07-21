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

---

## 8. UI Border Rules (KHÔNG được vi phạm)

> **Nguyên tắc: Ít border hơn = giao diện đẹp hơn.**

### 8.1 Global QFrame
```python
# ĐÚNG — Frame chứa nội dung KHÔNG có border, chỉ dùng background + border-radius
g = QFrame(); g.setStyleSheet("QFrame { background: white; border: none; border-radius: 8px; }")

# SAI — Tạo double-border vì QLineEdit bên trong cũng có border
g = QFrame(); g.setStyleSheet("QFrame { border: 1px solid #e2e8f0; }")
```

### 8.2 QLineEdit / QComboBox
- Global theme (`components.py`) đã định nghĩa `border: none; border-bottom: 1px solid #cbd5e1;`
- **KHÔNG được** set thêm `border:` inline trên QLineEdit/QComboBox trừ khi bị yêu cầu rõ ràng
- Khi cần scope riêng: dùng `objectName` + CSS selector `QLineEdit#myName { ... }`

### 8.3 QFrame tách biệt (separator)
```python
# ĐÚNG — Separator dùng HLine với border-top
sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
sep.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;")

# SAI — setStyleSheet("color: #e2e8f0;") trên HLine không có tác dụng trên nền trắng
```

### 8.4 QTableWidget
- Chỉ có border ngoài cùng, gridline-color đã được set trong theme
- **KHÔNG thêm** border inline cho table cells hoặc header

---

## 9. Repository Method Rules

Trước khi gọi method trên repository, PHẢI kiểm tra method có tồn tại không:

| Repository | Các method có sẵn |
|-----------|-------------------|
| `SQLiteLaneRepository` | `get_by_id`, `list_active`, `create`, `update` |
| `SQLiteVehicleRepository` | `create`, `get_by_rfid`, `list_by_subscriber` |
| `SQLiteSessionRepository` | `list_recent(branch_id, limit)`, `get_active_by_plate` |
| `SQLiteSettingsRepository` | `get_settings()`, `save_settings(data: dict)` |

> **KHÔNG dùng** `list_all()` trên `SQLiteVehicleRepository` hay `list_by_branch()` trên `SQLiteLaneRepository` — các method này không tồn tại.
> Dùng `_vehicle_name_map(settings)` để lấy map loại xe.

---

## 10. UI Design Philosophy (Frontend Design Rules)

> Áp dụng khi thiết kế lại hoặc xây dựng trang mới trong ứng dụng PySide6.

### 10.1 Nguyên tắc chung

Tiếp cận như **design lead tại một studio nhỏ** — mỗi màn hình phải có bản sắc thị giác riêng, không thể nhầm lẫn với template mặc định. Client đã từ chối các đề xuất trông như template.

**Trước khi code bất cứ thứ gì, phải xác định:**
1. Màn hình này phục vụ **ai** (operator bãi xe, quản lý, admin)?
2. **Công việc duy nhất** của màn hình này là gì?
3. **Một rủi ro thẩm mỹ có chủ đích** mà bạn có thể biện hộ?

### 10.2 Thiết kế bằng nội dung thật

- **KHÔNG dùng** placeholder text kiểu "Lorem ipsum" hay label chung chung như "Thông tin"
- Lấy từ vựng từ **domain bãi xe** cụ thể: biển số, ca trực, RFID, cổng chắn, lượt xe, doanh thu ca
- Trạng thái rỗng (empty state) = **lời mời hành động**, không phải thông báo buồn tẻ
  - ❌ "Chưa có dữ liệu"
  - ✅ "Chưa có xe trong bãi — mở ca làm việc để bắt đầu ghi nhận"

### 10.3 Palette và Typography

**Palette chuẩn (đã định nghĩa trong `components.py`)**:
- Sidebar: `#0f172a` (dark navy)
- Background: `#f8fafc`
- Card/Panel: `#ffffff`
- Accent primary: `#f97316` (orange — màu chủ đạo, dùng có tiết chế)
- Accent success: `#10b981`, danger: `#ef4444`, info: `#3b82f6`

**Quy tắc typography:**
- Dùng font `Segoe UI` / `Inter` — đã set trong THEME global
- Tiêu đề trang: `font-size: 24px; font-weight: 700`
- Metric lớn (số liệu dashboard): `font-size: 28–36px; font-weight: 800`
- Label phụ/caption: `font-size: 11–12px; color: #64748b`
- **KHÔNG dùng** font-size dưới 10px hay trên 40px trừ khi có lý do rõ ràng

### 10.4 Layout và Cấu trúc

**Nguyên tắc:**
- Cấu trúc phải **mã hóa thông tin**, không phải trang trí
- Dùng **spacing nhất quán**: 8, 12, 16, 20, 24, 28px
- Grid/panel chia theo tỷ lệ có nghĩa: 3:2, 2:1, 1:1 — không phải ngẫu nhiên
- **Mỗi trang có một điểm nhấn thị giác duy nhất** (signature element)
  - Dashboard: 4 metric cards gradient màu sắc
  - Operations: lane card với nút hành động lớn
  - Settings: form sạch với section divider rõ ràng

**ASCII wireframe trước khi code** nếu layout phức tạp:
```
┌─ Metric ──┬─ Metric ──┬─ Metric ──┬─ Metric ─┐
│           │           │           │          │
├─ Lanes ───┴──────────┬─ Chart ───────────────┤
│ Lane 1 → [Chờ xe]    │ 0.9 ▂▃▅▇ 23h         │
│ Lane 2 ← [Đang có]   │                       │
├─ Table (3fr) ────────┴─ Stats (2fr) ─────────┤
│ Biển số │ Loại │ Thời gian  │ Thuê bao: 0    │
└──────────────────────────────────────────────┘
```

### 10.5 Motion và Interaction

- **Dùng motion có mục đích**, không rải hiệu ứng khắp nơi
- Micro-interaction đáng dùng trong PySide6:
  - Hover state trên button/row table: thay đổi background color (qua CSS)
  - `setCursor(Qt.CursorShape.PointingHandCursor)` cho mọi nút có thể click
  - Thay đổi màu badge theo trạng thái dữ liệu thật
- **KHÔNG animate** những thứ không carry thông tin

### 10.6 Ngôn ngữ UI (Copy)

- **Active voice**: "Lưu thay đổi" không phải "Submit"; "Mở ca" không phải "Bắt đầu"
- **Nhất quán**: nút gọi là "Xóa" thì toast cũng phải nói "Đã xóa"
- **Error messages**: nói rõ vấn đề + cách fix
  - ❌ "Đã xảy ra lỗi"
  - ✅ "Không thể lưu: Biển số không được để trống"
- **Label từ góc nhìn người dùng**, không từ góc nhìn hệ thống:
  - ❌ "Session ID", "FK violation"
  - ✅ "Phiên gửi xe", "Biển số đã tồn tại"

### 10.7 Checklist trước khi submit thiết kế mới

- [ ] Có **signature element** không bị lẫn với màn hình khác
- [ ] Palette chỉ dùng màu từ token system (không thêm màu ad-hoc vô tội vạ)
- [ ] Spacing nhất quán theo bội số 4px
- [ ] Empty state có **lời mời hành động** cụ thể
- [ ] Button text là **động từ rõ ràng**
- [ ] `PointingHandCursor` cho mọi phần tử tương tác
- [ ] Không có border thừa (xem Rule 8)
- [ ] Đã tự hỏi: *"Màn hình này trông có giống template mặc định không?"*
