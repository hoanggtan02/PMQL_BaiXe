# Feature Map: Tài khoản người dùng (Accounts)

## Chức năng
Quản lý tài khoản nhân viên, phân quyền theo role.

## Files cần đọc khi sửa

```
src/pmql/ui/app.py
  → def accounts_page()            # UI trang tài khoản
  → def load_accounts()            # Load bảng users
  → def add_account_dialog()       # Dialog tạo tài khoản
  → def edit_account_dialog()      # Dialog sửa tài khoản
  → def delete_account()           # Xóa
  → async def _user_entities()     # List[User]
  → async def _create_user()       # Tạo user mới
  → async def _update_user()       # Cập nhật
  → async def _delete_user()       # Xóa

src/pmql/application/use_cases/auth/
  → create_user_use_case.py        # CreateUserInput, CreateUserUseCase
  → login_use_case.py              # LoginInput, LoginUseCase

src/pmql/application/use_cases/management_ops.py
  → UserUpdateInput, UserManagementUseCase

src/pmql/domain/entities/user.py
src/pmql/application/security.py             # Permission codes
src/pmql/application/ports/security_port.py  # IPasswordHasher
src/pmql/infrastructure/security/
  → password_hasher.py             # PBKDF2PasswordHasher
  → jwt_token_service.py           # JwtTokenService

src/pmql/infrastructure/persistence/sqlite/
  → repositories.py → SQLiteUserRepository
  → authorization_repository.py → SQLiteAuthorizationRepository
```

## User Entity Fields
```python
User:
  id, branch_id, username, password_hash
  full_name: str
  role: str          # VD: "admin", "operator", "supervisor"
  is_active: bool
```

## Permission System
```python
# Permissions check trong UI:
if "lane.operate" not in self.permission_codes: # ẩn menu
# Codes: lane.operate, session.view, alert.manage, shift.manage,
#        subscriber.manage, card.manage, fee.manage, lane.view, user.manage
```

## UI Layout (accounts_page)
```
Header: tiêu đề + nút [+ Thêm tài khoản]
Table: Tên đăng nhập | Họ tên | Vai trò | Trạng thái | Thao tác

Dialog add/edit:
  - Tên đăng nhập (readonly khi edit)
  - Mật khẩu (QLineEdit, password mode)
  - Họ tên
  - Vai trò (QComboBox)
  - Trạng thái (nếu edit)
```

## ⚠️ Lưu ý
- Password được hash bằng PBKDF2PasswordHasher trước khi lưu
- Admin không thể tự xóa mình
- Role string là free-form (không enum cứng), ảnh hưởng đến permissions
