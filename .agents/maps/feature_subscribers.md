# Feature Map: Thuê bao (Subscribers)

## Chức năng
Quản lý khách hàng thuê bao dài hạn, mỗi thuê bao có nhiều phương tiện đăng ký.

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def subscriber_page()          # UI trang thuê bao
  → def load_subscribers()         # Load bảng (có vehicles inline)
  → def subscriber_dialog()        # Dialog thêm/sửa (shared cho add + edit)
  → def add_subscriber()           # Wrapper gọi subscriber_dialog()
  → def edit_subscriber()          # Wrapper gọi subscriber_dialog(sub, vehicles)
  → def delete_subscriber()        # Xóa mềm
  → def fill_vehicle_combo()       # Điền combo loại xe (dùng chung)
  → async def _subscriber_with_vehicles()   # Lấy (Subscriber, [Vehicle]) pairs
  → async def _subscriber_entities()        # Lấy danh sách Subscriber (cho dropdown)
  → async def _vehicle_name_map()           # {vehicle_type_code: display_name}
  → async def _create_subscriber()          # Tạo mới
  → async def _update_subscriber()          # Cập nhật + sync vehicles
  → async def _delete_subscriber()          # Xóa

src/pmql/application/use_cases/subscriber_ops/
  → register_subscriber_use_case.py   # RegisterSubscriberInput, RegisterSubscriberUseCase
    # Tạo Subscriber + danh sách Vehicle cùng lúc

src/pmql/application/use_cases/management_ops.py
  → SubscriberUpdateInput              # subscriber_id, full_name, phone, identity_card,
                                       # vehicles: list[{plate_number, vehicle_type}],
                                       # valid_from, valid_until, email, is_active
  → SubscriberManagementUseCase.update()  # Sync vehicles: xóa cũ → tạo mới
  → SubscriberManagementUseCase.delete()

src/pmql/domain/entities/subscriber.py
src/pmql/domain/entities/vehicle.py

src/pmql/application/ports/repositories.py
  → ISubscriberRepository: create, update, delete, list_all, get_by_id, get_by_vehicle_type
  → IVehicleRepository: create, update, delete, list_by_subscriber, get_by_plate, get_by_rfid

src/pmql/infrastructure/persistence/sqlite/repositories.py
  → SQLiteSubscriberRepository
  → SQLiteVehicleRepository (có list_by_subscriber và delete)

src/pmql/infrastructure/persistence/sqlite/models.py
  → SubscriberModel (có identity_card column — migration đã có)
  → VehicleModel
```

## Data flow
```
UI load_subscribers():
  asyncio.run(_subscriber_with_vehicles(settings))  
    → SQLiteSubscriberRepository.list_all() + SQLiteVehicleRepository per subscriber

UI subscriber_dialog() → Save:
  if new: asyncio.run(_create_subscriber(settings, full_name, phone, identity_card,
                                          vehicles_list, valid_from, valid_until, email))
    → RegisterSubscriberUseCase.execute(RegisterSubscriberInput)
    → tạo Subscriber + từng Vehicle

  if edit: asyncio.run(_update_subscriber(settings, sub_id, ...))
    → SubscriberManagementUseCase.update(SubscriberUpdateInput)
    → xóa vehicles cũ, tạo vehicles mới
```

## Subscriber Entity Fields
```python
Subscriber:
  id, branch_id, full_name, phone, email
  identity_card: str    # CMND/CCCD
  vehicle_type: str     # loại xe chính (legacy — nay dùng Vehicle table)
  valid_from: date
  valid_until: date
  is_active: bool

Vehicle:
  id, branch_id, plate_number, vehicle_type
  rfid_tag: str | None
  subscriber_id: str | None   # FK tới Subscriber
```

## UI Layout (subscriber_page)
```
Header: tiêu đề + nút [+ Thêm thuê bao]
Table: Họ tên | Số điện thoại | CMND/CCCD | Phương tiện đăng ký | Hiệu lực đến | Trạng thái | Thao tác(210px)

Dialog subscriber_dialog():
  Grid left: Họ tên, Số ĐT, Email, CMND/CCCD, Hiệu lực từ, Hiệu lực đến, [Trạng thái nếu edit]
  Grid right (GroupBox "Phương tiện đăng ký"):
    Danh sách động: [Biển số] [Loại xe] [✕]
    Nút [+ Thêm xe]
  Footer: [Hủy] [Lưu]
```

## ⚠️ Lưu ý
- `vehicles_list` truyền vào `_create_subscriber` là `list[dict]`: `[{"plate_number": "...", "vehicle_type": "..."}]`
- Khi update subscriber, TOÀN BỘ vehicles cũ bị xóa và tạo lại
- Column `identity_card` trong SubscriberModel có migration inline trong `database.py`
