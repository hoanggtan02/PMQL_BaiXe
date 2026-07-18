# PMQL Bãi Xe

PMQL Bãi Xe là ứng dụng máy tính để quản lý bãi giữ xe: ghi nhận xe vào/ra,
tính phí, theo dõi ca làm việc, quản lý thuê bao tháng và thẻ RFID.

## Mục lục

- [Cài đặt](#cài-đặt)
- [Khởi động](#khởi-động)
- [Đăng nhập](#đăng-nhập)
- [Các màn hình chính](#các-màn-hình-chính)
- [Lưu ý dữ liệu](#lưu-ý-dữ-liệu)

## Cài đặt

Cần có Python 3.12 hoặc mới hơn. Mở Command Prompt tại thư mục dự án và chạy:

```bat
python -m pip install -e ".[gui,dev]"
```

## Khởi động

Lần đầu sử dụng, tạo dữ liệu ban đầu:

```bat
python -m pmql.main init-db
```

Sau đó mở ứng dụng:

```bat
python -m pmql.main ui
```

## Đăng nhập

Tài khoản ban đầu:

| Tên đăng nhập | Mật khẩu |
| --- | --- |
| `admin` | `123` |

Nếu tài khoản `admin` đã tồn tại với mật khẩu khác:

```bat
python -m pmql.main reset-password --username admin --password 123
```

## Các màn hình chính

- **Tổng quan:** số xe trong bãi, lượt xe và doanh thu.
- **Vận hành làn:** mở ca, ghi xe vào/ra và xem trạng thái làn.
- **Phiên gửi xe:** theo dõi các xe đang gửi và lịch sử xe ra.
- **Thuê bao:** thêm, sửa, xóa mềm thuê bao tháng.
- **Thẻ xe:** nhập mã RFID, gán thẻ cho thuê bao, khóa/mở thẻ.
- **Biểu phí:** tạo, sửa và xóa mềm quy tắc tính phí.
- **Cấu hình làn:** thêm làn cùng thông tin camera, RFID và barrier.
- **Tài khoản & phân quyền:** tạo tài khoản, tạo role và chọn quyền cho role.

## Lưu ý dữ liệu

Dữ liệu được lưu cục bộ trong `data/parking_local.db`. Thao tác xóa chỉ ẩn
dữ liệu khỏi danh sách, không xóa vĩnh viễn lịch sử vận hành.
