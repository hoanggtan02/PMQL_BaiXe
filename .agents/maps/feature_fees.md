# Feature Map: Biểu phí (Fee Rules)

## Chức năng
Cấu hình quy tắc tính phí theo loại xe, có tính phí thử và lịch sử.

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def fee_page()                 # UI trang biểu phí (3 tabs)
  → def toggle_fee_rule()          # Bật/tắt quy tắc
  → def add_fee_rule()             # Dialog thêm
  → def edit_fee_rule()            # Dialog sửa
  → def delete_fee_rule()          # Xóa mềm
  → async def _fee_rules()         # List[FeeRule]
  → async def _create_fee_rule()   # Tạo mới
  → async def _update_fee_rule()   # Cập nhật
  → async def _delete_fee_rule()   # Xóa
  → async def _vehicle_name_map()  # {vehicle_type_code: display_name}

src/pmql/domain/entities/fee_rule.py
src/pmql/domain/services/fee_calculator.py   # FeeCalculator.calculate(entry, exit)

src/pmql/application/use_cases/management_ops.py
  → FeeRuleInput, FeeRuleManagementUseCase

src/pmql/application/ports/repositories.py → IFeeRuleRepository
src/pmql/infrastructure/persistence/sqlite/repositories.py → SQLiteFeeRuleRepository
```

## FeeRule Entity Fields
```python
FeeRule:
  id, branch_id, name
  vehicle_type: str       # code từ VehicleTypeModel (vd: "xe_may", "o_to")
  block_minutes: int      # đơn vị tính phí (VD: 60 phút = 1 block)
  price_per_block: int    # giá mỗi block (VND)
  free_minutes: int       # phút miễn phí đầu
  day_max: int | None     # trần phí cả ngày
  night_surcharge: int    # phụ thu ban đêm
  is_active: bool
```

## FeeCalculator
```python
# Dùng khi tính phí thử hoặc tính phí khi xe ra
from pmql.domain.services.fee_calculator import FeeCalculator
calc = FeeCalculator(rule)  # rule là FeeRule entity
fee = calc.calculate(entry_datetime, exit_datetime)  # → int (VND)
```

## UI Layout (fee_page) — 3 TABS
```
Header: tiêu đề + nút [+ Thêm quy tắc]

Tab 1 "Quy tắc phí":
  Grid (3 cột) các card:
    Mỗi card:
      - Tên quy tắc + icon loại xe
      - Badge: [✔ Đang áp dụng] hoặc [− Đã tắt]  ← màu khác nhau
      - Border card: #3b82f6 nếu active, #e2e8f0 nếu inactive
      - Stats: GIÁ/BLOCK | BLOCK | MIỄN PHÍ | [TRẦN/NGÀY] | [PHỤ ĐÊM]
      - Actions: [Sửa] [Bật/Tắt] ... [Xóa]

Tab 2 "Tính phí thử":
  - Dropdown: Loại xe
  - DateTimeEdit: Giờ vào / Giờ ra (có calendar popup)
  - Nút [Tính phí]
  - Result frame (ẩn cho đến khi tính):
    Thời gian gửi | Quy tắc áp dụng | Tổng phí

Tab 3 "Lịch sử":
  Bảng: Quy tắc | Loại xe | Giá/block | Block | Miễn phí | Trần/ngày | Trạng thái
```

## ⚠️ Lưu ý
- `toggle_fee_rule()` truy cập DB trực tiếp (không qua use case) để flip `is_active`
- `vehicle_type` phải khớp với code trong bảng `vehicle_types` (xem `_vehicle_name_map()`)
- Nếu không có rule active cho loại xe → tính phí thử sẽ báo lỗi
