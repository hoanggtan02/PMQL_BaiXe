# PMQL Bãi Xe

Hệ thống quản lý bãi xe **local-first**: mỗi chi nhánh chạy trên SQLite tại chỗ
(hoạt động được cả khi mất mạng), đồng bộ định kỳ lên MySQL trung tâm.
Kiến trúc theo hướng **Clean Architecture** (domain → application → infrastructure).

## Kiến trúc thư mục

```
src/pmql/
├── domain/            # Entities, value objects, domain services — KHÔNG phụ thuộc framework
├── application/       # Use cases + ports (interfaces) — không import infrastructure
├── infrastructure/    # Cài đặt cụ thể: SQLite repos, mock hardware, outbox writer
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

## Chạy test

```bash
pytest
```

## Hiện trạng — đã làm / còn thiếu

**Đã có:** domain entities, value objects, `FeeCalculator`, 2 use case (vào/ra
xe), toàn bộ port interfaces, repository SQLite, mock hardware, outbox ghi
transactional cho đồng bộ, CLI chạy thử end-to-end.

**Chưa có (cần làm tiếp):**
- Adapter phần cứng thật (camera/OpenCV, ANPR, đầu đọc RFID qua pyserial, điều
  khiển barrier qua pymodbus) — hiện chỉ có bản mock trong
  `infrastructure/hardware/mock_hardware.py`.
- Worker đẩy dữ liệu từ `sync_outbox` (SQLite) lên MySQL trung tâm.
- Alembic migrations cho schema (hiện dùng `create_all` tiện cho dev, chưa dùng
  được cho migration production).
- Giao diện PySide6 (Desktop UI) cho nhân viên vận hành.
- Use case: mở/đóng ca làm việc, quản lý thuê bao, quản lý user, xử lý alert.
- Test coverage cho tầng infrastructure (mới có test cho domain/application).

## Quy ước quan trọng

- **Tiền tệ luôn là `int` (VND)** — không bao giờ dùng `float` cho tiền
  (xem `domain/value_objects/money.py`).
- Mỗi ghi dữ liệu nghiệp vụ đi kèm một bản ghi trong `sync_outbox` **trong cùng
  transaction** — đảm bảo không bao giờ mất sự kiện đồng bộ khi mất điện/crash.
