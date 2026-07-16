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
```

File DB nằm ở `./data/parking_local.db` (xem `LOCAL_DATABASE_URL` trong `.env`).

Lưu ý: docstring của `main.py` từng nhắc tới lệnh `list-sessions` nhưng lệnh
này **chưa được đăng ký** trong `build_parser()` — vẫn còn thiếu, xem mục
"Hiện trạng" bên dưới.

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
- **Mới thêm:** model + repository SQLite cho `User`, `Shift`, `Alert`,
  `Device` — các port (`IUserRepository`, `IShiftRepository`,
  `IAlertRepository`, `IDeviceRepository`) đã tồn tại từ trước nhưng
  **chưa có cài đặt cụ thể nào** cho tới đợt này.
- **Mới thêm:** use case mở/đóng ca làm việc (`OpenShiftUseCase` /
  `CloseShiftUseCase`), đăng nhập/tạo tài khoản (`LoginUseCase` /
  `CreateUserUseCase` — băm mật khẩu bằng PBKDF2-SHA256, thuần thư viện
  chuẩn, không thêm dependency mới), đăng ký thuê bao
  (`RegisterSubscriberUseCase`), xác nhận alert (`AcknowledgeAlertUseCase`).
- **Mới thêm:** `ParkingSession.shift_id` — trước đây `list_by_shift()` luôn
  trả về *toàn bộ* bảng sessions bất kể `shift_id` truyền vào (không có cột
  để lọc). Giờ session được gắn với ca làm việc đang mở tại thời điểm xe vào
  (`VehicleEntryInput.shift_id`), và `list_by_shift()` lọc đúng theo đó — đây
  là điều kiện để `CloseShiftUseCase` tính đúng `total_sessions` /
  `total_revenue`.
- **Đã sửa lỗi:** `VehicleExitUseCase` tra cứu phiên đang hoạt động bằng RFID
  bị sai — `ParkingSession.rfid_card_id` lưu **id nội bộ của Card**, không
  phải mã RFID quét được, nhưng code cũ so sánh trực tiếp với mã quét thô.
  Hậu quả: xe vào bằng thẻ RFID sẽ **không bao giờ được tìm thấy khi ra bằng
  RFID** (chỉ tìm được nếu người vận hành nhập thêm biển số). Đã sửa để tra
  Card trước rồi mới tra phiên theo `card.id`, giống logic lúc vào. Có test
  hồi quy trong `tests/test_shift_and_auth.py`.

### Chưa có (cần làm tiếp)

- Adapter phần cứng thật (camera/OpenCV, ANPR, đầu đọc RFID qua pyserial,
  điều khiển barrier qua pymodbus) — hiện chỉ có bản mock trong
  `infrastructure/hardware/mock_hardware.py`.
- Worker đẩy dữ liệu từ `sync_outbox` (SQLite) lên MySQL trung tâm.
- Alembic migrations cho schema (hiện dùng `create_all` tiện cho dev, chưa
  dùng được cho migration production — schema mới thêm ở đợt này
  (`users`, `shifts`, `alerts`, `devices`, cột `sessions.shift_id`) cũng chỉ
  chạy qua `create_all`, cần viết migration thật khi lên production).
- Giao diện PySide6 (Desktop UI) cho nhân viên vận hành.
- CLI (`main.py`) chưa có lệnh cho: mở/đóng ca, đăng nhập, tạo user, đăng ký
  thuê bao, xác nhận alert, `list-sessions` — các use case đã có sẵn ở tầng
  application, chỉ còn thiếu phần composition-root/CLI để gọi chúng.
- Phát hành token/session sau khi đăng nhập (`LoginUseCase` hiện chỉ xác thực
  và trả về thông tin user; chưa có JWT hay cơ chế phiên đăng nhập nào).
- Phân quyền theo `role` (`OPERATOR` / `SUPERVISOR` / `ADMIN`) — enum tồn tại
  trên entity `User` nhưng chưa có use case/middleware nào kiểm tra quyền.
- `IFeeRuleRepository` chưa có `delete`.
- Test coverage cho tầng infrastructure ngoài các test tích hợp hiện có
  (mới có test cho domain/application qua SQLite thật, chưa test riêng từng
  repository/mapper).
- Xử lý múi giờ: toàn bộ timestamp hiện là timezone-naive UTC
  (`datetime.utcnow()`), phù hợp cho MVP nhưng nên chuyển sang
  timezone-aware trước khi lên production.

## Quy ước quan trọng

- **Tiền tệ luôn là `int` (VND)** — không bao giờ dùng `float` cho tiền
  (xem `domain/value_objects/money.py`).
- Mỗi ghi dữ liệu nghiệp vụ đi kèm một bản ghi trong `sync_outbox` **trong cùng
  transaction** — đảm bảo không bao giờ mất sự kiện đồng bộ khi mất điện/crash.
- Mật khẩu **không bao giờ** lưu dạng plain text — luôn đi qua
  `IPasswordHasher` (cài đặt mặc định: PBKDF2-SHA256, 260,000 vòng lặp).
- `ParkingSession.shift_id` nên luôn được truyền khi gọi
  `VehicleEntryUseCase` một khi hệ thống ca làm việc đã được bật lên trong
  UI/CLI — nếu để trống, phiên đó sẽ không được tính vào ca nào khi đóng ca.
