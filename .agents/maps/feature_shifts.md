# Feature Map: Ca làm việc (Shifts)

## Chức năng
Mở/đóng ca làm việc cho nhân viên, theo dõi doanh thu và lượt xe theo ca.

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def shift_page()               # UI trang ca làm việc (có 2 tab: Ca hiện tại / Lịch sử)
  → def add_shift()                # Dialog mở ca (từ shift_page — tab Ca hiện tại)
  → def open_shift()               # Dialog mở ca (từ header sidebar — nút "Mở ca")
  → def close_shift_dialog()       # Dialog đóng ca
  → def load_shifts()              # Load bảng lịch sử
  → def edit_shift()               # Sửa thông tin ca
  → def delete_shift()             # Xóa ca
  → async def _open_shift()        # Gọi OpenShiftUseCase
  → async def _close_shift()       # Gọi CloseShiftUseCase
  → async def _shift_entities()    # Lấy tất cả shifts
  → async def _delete_shift()      # Xóa shift

src/pmql/application/use_cases/shift_ops/
  → open_shift_use_case.py         # OpenShiftInput, OpenShiftUseCase
  → close_shift_use_case.py        # CloseShiftInput, CloseShiftUseCase

src/pmql/application/use_cases/management_ops.py
  → ShiftInput, ShiftManagementUseCase   # CRUD ca

src/pmql/domain/entities/shift.py        # Shift entity + shift.close()

src/pmql/application/ports/repositories.py → IShiftRepository
src/pmql/infrastructure/persistence/sqlite/repositories.py → SQLiteShiftRepository
src/pmql/infrastructure/persistence/sqlite/database.py
  # Migration: lane_id, note, opening_cash, closing_cash, close_note
```

## Data flow
```
UI (add_shift / open_shift dialog)
  → asyncio.run(_open_shift(settings, user_id, lane_id, note, opening_cash))
  → OpenShiftUseCase.execute(OpenShiftInput)
  → IShiftRepository.create(shift)

UI (close_shift_dialog)
  → asyncio.run(_close_shift(settings, shift_id, closing_cash, close_note))
  → CloseShiftUseCase.execute(CloseShiftInput)
  → shift.close(end_time, total_sessions, total_revenue, ...)
  → IShiftRepository.update(shift)
```

## Shift Entity Fields
```python
Shift:
  id, branch_id, operator_id
  lane_id: str | None      # làn phụ trách (None = tất cả)
  note: str                # loại ca (Ca sáng, Ca chiều...)
  opening_cash: int        # tiền đầu ca
  closing_cash: int        # tiền cuối ca
  close_note: str          # ghi chú đóng ca
  start_time, end_time
  total_sessions: int
  total_revenue: int
  status: "OPEN" | "CLOSED"
```

## UI Layout (shift_page)
```
Tab 1 "Ca hiện tại":
  - Banner hiển thị ca đang mở (tên ca, thời gian, % hoàn thành)
  - Stats grid: tổng lượt xe, hoàn thành, đang gửi, doanh thu
  - Nút [Mở ca làm việc] / [Đóng ca]

Tab 2 "Lịch sử ca":
  - Thanh tìm kiếm
  - Bảng: Mã ca | Nhân viên | Loại ca | Làn | Tiền đầu ca | Doanh thu | Bắt đầu | Kết thúc | Trạng thái | Thao tác
```

## ⚠️ Lưu ý
- `add_shift()` (trong shift_page) và `open_shift()` (trong sidebar) là 2 dialog KHÁC NHAU
- Cả hai đều gọi cùng `_open_shift()` async helper
- Khi thêm field mới vào dialog → cập nhật cả 2 nơi hoặc refactor thành 1 hàm dùng chung
