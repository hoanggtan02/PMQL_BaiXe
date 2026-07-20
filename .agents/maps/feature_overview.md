# Feature Map: Tổng quan / Dashboard (Overview)

## Chức năng
Màn hình tổng quan: số liệu hôm nay, xe đang trong bãi (live table).

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def overview_page()            # Tạo layout + các card số liệu
  → def refresh_live()             # Cập nhật tất cả số liệu live (gọi mỗi khi navigate)
  → async def _active_sessions()   # Các xe đang trong bãi
  → async def _session_count_today()  # Tổng lượt xe hôm nay
  → async def _revenue_today()     # Doanh thu hôm nay
  → async def _alert_count()       # Số cảnh báo chưa xử lý
```

## UI Layout (overview_page)
```
Grid (4 cột) metric cards:
  [XE ĐANG TRONG BÃI] [LƯỢT XE HÔM NAY] [DOANH THU HÔM NAY] [CẢNH BÁO CHỜ XỬ LÝ]
  Màu: #2f66d0       #159947            #f06d1c              #cf3436

Panel "Xe đang trong bãi" (live table):
  Cột: Biển số | Trạng thái | Thời điểm vào | Làn vào
  Minimum 6 rows
```

## refresh_live() được gọi khi
```python
# Trong go() method:
if key in {"overview", "operations"}: self.refresh_live()
# Cũng được gọi sau khi mở/đóng ca
```

## ⚠️ Lưu ý
- 4 metric values được lưu trong `self.overview_values: list[QLabel]`
- live_table được lưu trong `self.live_table`
- Shift button trong header: `self.shift_button` (nút "Mở ca" / "Ca đang hoạt động")
