# Feature Map: Cấu hình làn xe (Lanes)

## Chức năng
Thêm/sửa/xóa làn xe, cấu hình thiết bị (RFID, camera, barrier), bật/tắt làn.

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def lane_page()                # UI trang cấu hình làn (Grid cards)
  → def load_lanes()               # Render lại grid làn
  → def show_lane_modal()          # Dialog thêm/sửa làn
  → def add_lane()                 # Wrapper
  → def edit_lane()                # Wrapper
  → def delete_lane()              # Xóa mềm
  → async def _lanes()             # List[Lane]
  → async def _create_lane()       # Tạo làn mới
  → async def _update_lane()       # Cập nhật làn
  → async def _delete_lane()       # Xóa làn

src/pmql/domain/entities/lane.py

src/pmql/application/ports/repositories.py → ILaneRepository
src/pmql/infrastructure/persistence/sqlite/repositories.py → SQLiteLaneRepository
```

## Lane Entity Fields
```python
Lane:
  id, branch_id, name
  direction: "IN" | "OUT" | "INOUT"
  camera_source: str | None      # URL/path camera
  rfid_device_id: str | None     # ID đầu đọc RFID
  barrier_device_id: str | None  # ID barrier (cần)
  is_active: bool
```

## UI Layout (lane_page)
```
Header: [↺ Lịch sử thay đổi] | "| N làn đang cấu hình" | [+ Thêm làn xe]
ScrollArea → Grid (2 cột) các card:
  Mỗi card:
    - Tên làn + số xe đang gửi (counter)
    - Tags: [↗ Xe vào / ↙ Xe ra / ↔ Hai chiều] [● Hoạt động / ○ Tắt]
    - "THIẾT BỊ LẮP ĐẶT": [💳 Đầu đọc thẻ] [📷 Camera] [🚧 Barrier]
    - Trạng thái: "Chờ xe"
    - Actions: [✎ Sửa cấu hình] [🗑]

Dialog show_lane_modal():
  - Tên làn (QLineEdit)
  - Hướng (QComboBox: Xe vào / Xe ra / Hai chiều)
  - Trạng thái (QComboBox: Hoạt động / Tắt)
  - Camera source (QLineEdit)
  - RFID device (QLineEdit)
  - Barrier device (QLineEdit)
  Footer: [Hủy] [💾 Lưu cấu hình]
```

## Direction Map (trong dialog)
```python
dir_map = {"Xe vào": "IN", "Xe ra": "OUT", "Hai chiều": "INOUT"}
rev_dir_map = {0: "IN", 1: "OUT", 2: "INOUT"}  # theo index combo
```

## ⚠️ Lưu ý
- `load_lanes()` xóa grid cũ rồi render lại từ đầu (không dùng reload_page)
- Số xe đang gửi hiện là placeholder "0" — cần nối với ISessionRepository để hiển thị thực
- Nút "Lịch sử thay đổi" chưa có chức năng (placeholder)
