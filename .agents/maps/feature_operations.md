# Feature Map: Vận hành làn xe (Operations)

## Chức năng
Xe vào / xe ra theo làn — scan RFID hoặc nhập biển số, tính phí khi ra.

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def operations_page()          # UI trang vận hành
  → def refresh_live()             # Cập nhật live feed
  → async def _active_sessions()   # Lấy xe đang gửi
  → async def _do_entry()          # Ghi nhận xe vào
  → async def _do_exit()           # Ghi nhận xe ra + tính phí

src/pmql/application/use_cases/lane_ops/
  → vehicle_entry_use_case.py      # VehicleEntryInput, VehicleEntryUseCase
  → vehicle_exit_use_case.py       # VehicleExitInput, VehicleExitUseCase

src/pmql/domain/entities/session.py   # ParkingSession entity
src/pmql/domain/services/fee_calculator.py  # Tính phí

src/pmql/application/ports/repositories.py
  → ISessionRepository
  → IVehicleRepository
  → IFeeRuleRepository

src/pmql/infrastructure/persistence/sqlite/repositories.py
  → SQLiteSessionRepository
```

## Data flow
```
UI (operations_page) 
  → asyncio.run(_do_entry/exit(settings, ...))
  → VehicleEntryUseCase / VehicleExitUseCase
  → ISessionRepository.create/update
  → IFeeRuleRepository.get_active_by_vehicle_type
  → FeeCalculator.calculate(entry_time, exit_time)
```

## Entities quan trọng
```python
ParkingSession:
  plate_number, vehicle_type, entry_time, exit_time
  lane_id, shift_id, fee, status ("ACTIVE"/"COMPLETED")
```

## UI Layout
- Toolbar: chọn làn, bộ lọc trạng thái, nút Làm mới
- Bảng xe đang gửi (live): biển số, loại xe, thời gian vào, trạng thái
- Form nhập: biển số / RFID → nút Vào / Ra
- Hiển thị phí khi xe ra
