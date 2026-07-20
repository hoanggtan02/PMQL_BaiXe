# Feature Map: Thẻ RFID (Cards)

## Chức năng
Quản lý thẻ RFID. Thẻ có 2 loại (GUEST/SUBSCRIBER) và 4 trạng thái.

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def card_page()                # UI trang thẻ RFID
  → def load_cards()               # Load bảng với status badge màu
  → def card_dialog()              # Dialog thêm/sửa (shared)
  → def add_card()                 # Wrapper
  → def edit_card()                # Wrapper
  → def delete_card()              # Xóa mềm
  → async def _card_display_rows() # [(Card, subscriber_name)] — giải quyết FK
  → async def _card_entities()     # List[Card] thuần
  → async def _create_card()       # Tạo thẻ mới
  → async def _update_card()       # Cập nhật (type, subscriber_id, status)
  → async def _delete_card()       # Xóa

src/pmql/domain/entities/card.py

src/pmql/application/ports/repositories.py → ICardRepository
src/pmql/infrastructure/persistence/sqlite/repositories.py → SQLiteCardRepository

src/pmql/infrastructure/persistence/sqlite/models.py
  → CardModel (card_type, status columns — migration đã có)
  → database.py migration: card_type DEFAULT 'GUEST', status DEFAULT 'AVAILABLE'
```

## Card Entity Fields
```python
Card:
  id, branch_id
  rfid_code: str              # Mã UID của thẻ vật lý
  card_type: "GUEST" | "SUBSCRIBER"
  subscriber_id: str | None   # FK — chỉ có khi card_type == "SUBSCRIBER"
  vehicle_id: str | None      # FK vehicle (optional)
  is_active: bool
  status: "AVAILABLE" | "IN_USE" | "LOST" | "LOCKED"
```

## Status Colors (trong UI)
```python
STATUS_COLOR = {
    "AVAILABLE": "#22c55e",   # xanh lá
    "IN_USE":    "#3b82f6",   # xanh dương
    "LOST":      "#f59e0b",   # vàng
    "LOCKED":    "#ef4444",   # đỏ
}
```

## UI Layout (card_page)
```
Header: tiêu đề + nút [+ Thêm thẻ]
Table (action_col_width=210):
  Mã thẻ (UID) | Loại thẻ | Thuê bao | Trạng thái (badge widget) | Thao tác

Dialog card_dialog():
  - Mã UID (readonly khi edit)
  - Loại thẻ: [Vãng lai / Thuê bao]
  - Gán thuê bao: ComboBox (ẩn khi Vãng lai)
  - Trạng thái: ComboBox (chỉ hiện khi edit)
  Footer: [Hủy] [Lưu]
```

## ⚠️ Lưu ý
- Status badge là `QWidget` wrapper (không phải QTableWidgetItem) để hiển thị màu
- Khi card_type = "GUEST", subscriber_id phải là None
- `_card_display_rows()` resolve tên thuê bao từ subscriber_id trong 1 session
