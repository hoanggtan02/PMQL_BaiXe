# PMQL Bãi Xe

Hệ thống quản lý bãi xe **local-first**: mỗi chi nhánh chạy trên SQLite tại chỗ
(hoạt động được cả khi mất mạng), đồng bộ định kỳ lên MySQL trung tâm.
Kiến trúc theo hướng **Clean Architecture** (domain → application → infrastructure).

## Kiến trúc thư mục

```
src/pmql/
├── domain/            # Entities, value objects, domain services — KHÔNG phụ thuộc framework
├── application/       # Use cases + ports (interfaces) — không import infrastructure
├── infrastructure/    # Cài đặt cụ thể: SQLite repos, mock hardware, outbox writer, security
├── config/            # Settings đọc từ .env
└── main.py            # Composition root — CLI demo nối use case với adapter thật
```

Nguyên tắc: `domain` không phụ thuộc gì cả; `application` chỉ phụ thuộc `domain`
và các *port* (ABC) của chính nó; `infrastructure` implement các port đó.
`main.py` là nơi duy nhất được phép "biết" cả use case lẫn adapter cụ thể.

## Cài đặt

Yêu cầu Python >= 3.12.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env              # chỉnh các giá trị cho phù hợp
```

## Chạy thử (CLI demo, chưa cần phần cứng thật)

```bash
# 1. Tạo schema SQLite + seed 1 làn xe và 2 quy tắc phí mặc định
python -m pmql.main init-db

# 2. Xe vào
python -m pmql.main enter --plate 51F-12345 --type motorbike

# 3. Xe ra (tính phí tự động theo FeeCalculator)
python -m pmql.main exit --plate 51F-12345

# 4. Xem cac phien do xe gan day nhat (MOI: truoc day chi la docstring, chua co lenh)
python -m pmql.main list-sessions --limit 20
```

### Tài khoản, ca làm việc, thuê bao, alert (MỚI — đã nối CLI ở đợt này)

Các use case này đã tồn tại sẵn ở tầng `application` từ trước, nhưng
`main.py` trước đây **chưa đăng ký lệnh CLI nào** để gọi tới chúng. Đợt cập
nhật này bổ sung phần composition-root còn thiếu đó:

```bash
# Tạo tài khoản vận hành + đăng nhập
python -m pmql.main create-user --username an.nguyen --password s3cret --full-name "An Nguyen"
python -m pmql.main login --username an.nguyen --password s3cret

# Mở / đóng ca làm việc (đóng ca sẽ in tổng số phiên + doanh thu)
python -m pmql.main open-shift --operator-id an.nguyen
python -m pmql.main enter --plate 51F-12345 --type motorbike --shift-id <shift_id>
python -m pmql.main close-shift --operator-id an.nguyen

# Đăng ký thuê bao tháng (có thể phát hành thẻ RFID ngay)
python -m pmql.main register-subscriber --full-name "Le Van A" --phone 0900000000 \
    --vehicle-type motorbike --valid-from 2026-01-01 --valid-until 2026-12-31 --rfid AABBCC

# Xác nhận một alert hệ thống
python -m pmql.main ack-alert --alert-id <alert_id> --user-id an.nguyen
```

File DB nằm ở `./data/parking_local.db` (xem `LOCAL_DATABASE_URL` trong `.env`).

## Chạy test

```bash
pytest
```

## Hiện trạng — đã làm / còn thiếu

### Đã có (kể từ đợt cập nhật gần nhất)

- Domain entities, value objects, `FeeCalculator`.
- Use case vào/ra xe (`VehicleEntryUseCase` / `VehicleExitUseCase`), toàn bộ
  port interfaces, repository SQLite cho Lane/Vehicle/Card/Subscriber/FeeRule/
  Session, mock hardware, outbox ghi transactional cho đồng bộ, CLI chạy thử
  end-to-end.
- Model + repository SQLite cho `User`, `Shift`, `Alert`, `Device` — các port
  (`IUserRepository`, `IShiftRepository`, `IAlertRepository`,
  `IDeviceRepository`) đã tồn tại từ trước nhưng chưa có cài đặt cụ thể nào
  cho tới đợt trước.
- Use case mở/đóng ca làm việc (`OpenShiftUseCase` / `CloseShiftUseCase`),
  đăng nhập/tạo tài khoản (`LoginUseCase` / `CreateUserUseCase` — băm mật
  khẩu bằng PBKDF2-SHA256, thuần thư viện chuẩn, không thêm dependency
  mới), đăng ký thuê bao (`RegisterSubscriberUseCase`), xác nhận alert
  (`AcknowledgeAlertUseCase`).
- `ParkingSession.shift_id` — trước đây `list_by_shift()` luôn trả về *toàn
  bộ* bảng sessions bất kể `shift_id` truyền vào. Giờ session được gắn với
  ca làm việc đang mở tại thời điểm xe vào (`VehicleEntryInput.shift_id`),
  và `list_by_shift()` lọc đúng theo đó.
- Đã sửa lỗi `VehicleExitUseCase` tra cứu phiên đang hoạt động bằng RFID sai
  (so sánh trực tiếp mã quét thô thay vì id nội bộ của Card).

**Mới thêm ở đợt này:**

- **CLI (`main.py`) đã có đủ lệnh cho mọi use case đã tồn tại ở tầng
  application:** `list-sessions`, `create-user`, `login`, `open-shift`,
  `close-shift`, `register-subscriber`, `ack-alert` — trước đây các use case
  này có sẵn nhưng không thể gọi được từ CLI (composition root còn thiếu).
  Lệnh `enter` cũng nhận thêm `--shift-id` để có thể gắn phiên vào ca đang mở.
- **`IFeeRuleRepository.delete`** — trước đây interface và cài đặt SQLite
  chỉ có thể "tắt" một quy tắc phí qua `update(is_active=False)`, không có
  cách xóa hẳn. Đã thêm `delete(rule_id)` vào cả port và
  `SQLiteFeeRuleRepository`.
- **`ISessionRepository.list_recent` / `SQLiteSessionRepository.list_recent`**
  — trước đây không có cách nào liệt kê session theo chi nhánh; đây là điều
  kiện để lệnh CLI `list-sessions` hoạt động (lọc theo `branch_id`, sắp xếp
  theo `entry_time` giảm dần).
- Test hồi quy cho các phần trên: `tests/test_new_repo_and_cli_additions.py`.

### Chưa có (cố ý để lại — vượt phạm vi đợt sửa này)

Đợt này tập trung vào các mục nhỏ, có thể kiểm chứng ngay (CLI + 2 phương
thức repository còn thiếu). Các mục lớn dưới đây vẫn **chưa làm**, vì mỗi
mục đòi hỏi thiết kế/kiểm thử riêng đáng kể và không phù hợp để làm vội
trong cùng một đợt nhỏ:

- Adapter phần cứng thật (camera/OpenCV, ANPR, đầu đọc RFID qua pyserial,
  điều khiển barrier qua pymodbus) — hiện chỉ có bản mock trong
  `infrastructure/hardware/mock_hardware.py`.
- Worker đẩy dữ liệu từ `sync_outbox` (SQLite) lên MySQL trung tâm.
- Alembic migrations cho schema (hiện dùng `create_all` tiện cho dev, chưa
  dùng được cho migration production).
- Giao diện PySide6 (Desktop UI) cho nhân viên vận hành.
- Phát hành token/session sau khi đăng nhập (`LoginUseCase` hiện chỉ xác
  thực và trả về thông tin user; chưa có JWT hay cơ chế phiên đăng nhập
  nào — CLI hiện chỉ in kết quả đăng nhập ra màn hình).
- Phân quyền theo `role` (`OPERATOR` / `SUPERVISOR` / `ADMIN`) — enum tồn
  tại trên entity `User` nhưng chưa có use case/middleware nào kiểm tra
  quyền; CLI hiện không chặn thao tác theo role.
- Test coverage cho tầng infrastructure ngoài các test tích hợp hiện có
  (mới có test cho domain/application qua SQLite thật, chưa test riêng
  từng repository/mapper một cách biệt lập).
- Xử lý múi giờ: toàn bộ timestamp hiện là timezone-naive UTC
  (`datetime.utcnow()`), phù hợp cho MVP nhưng nên chuyển sang
  timezone-aware trước khi lên production.

> Lưu ý môi trường xây dựng đợt này: các file đã được kiểm tra cú pháp bằng
> `python -m py_compile` cho toàn bộ `src/` và `tests/`, nhưng bản build lại
> trong container không có mạng để tải `sqlalchemy`/`pytest`/... nên bộ test
> **chưa được chạy thực tế** ở đây — hãy chạy `pip install -e ".[dev]"` rồi
> `pytest` ở máy có mạng để xác nhận trước khi merge.

## Quy ước quan trọng

- **Tiền tệ luôn là `int` (VND)** — không bao giờ dùng `float` cho tiền
  (xem `domain/value_objects/money.py`).
- Mỗi ghi dữ liệu nghiệp vụ đi kèm một bản ghi trong `sync_outbox` **trong cùng
  transaction** — đảm bảo không bao giờ mất sự kiện đồng bộ khi mất điện/crash.
- Mật khẩu **không bao giờ** lưu dạng plain text — luôn đi qua
  `IPasswordHasher` (cài đặt mặc định: PBKDF2-SHA256, 260,000 vòng lặp).
- `ParkingSession.shift_id` nên luôn được truyền khi gọi
  `VehicleEntryUseCase` (CLI: `enter --shift-id ...`) một khi hệ thống ca
  làm việc đã được bật lên — nếu để trống, phiên đó sẽ không được tính vào
  ca nào khi đóng ca.
