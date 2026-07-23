from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class UserPageMixin:
    def accounts_page(self) -> QWidget:
            page, box = self.page(); header = QHBoxLayout(); h = label("Tài khoản & phân quyền", bold=True); h.setStyleSheet("font-size:24px;"); header.addWidget(h); header.addStretch(); roles = QPushButton("⚿ Vai trò & quyền"); roles.clicked.connect(self.manage_roles); header.addWidget(roles); create = QPushButton("+ Tạo tài khoản"); create.setObjectName("primary"); create.clicked.connect(self.create_account); header.addWidget(create); box.addLayout(header); self.user_table = self.make_table(["Tên đăng nhập", "Họ tên", "Vai trò", "Trạng thái", "Thao tác"]); box.addWidget(self.user_table, 1); self.load_users(); return page

    def load_users(self) -> None:
            if not hasattr(self, "user_table"): return
            try: users = asyncio.run(_users(self.settings))
            except Exception: return
            self.user_table.setRowCount(len(users))
            for r, user in enumerate(users):
                for c, value in enumerate((user.username, user.full_name, user.role, "Hoạt động" if user.is_active else "Đã khóa")): self.user_table.setItem(r, c, QTableWidgetItem(value))
                actions = QWidget(); actions.setMinimumHeight(38); action_row = QHBoxLayout(actions); action_row.setContentsMargins(4, 2, 4, 2)
                edit, remove = QPushButton("✎ Sửa"), QPushButton("Xóa"); remove.setObjectName("danger")
                edit.clicked.connect(lambda _=False, item=user: self.edit_account(item)); remove.clicked.connect(lambda _=False, item=user: self.delete_account(item))
                action_row.addWidget(edit); action_row.addWidget(remove); self.user_table.setCellWidget(r, 4, actions)

    def create_account(self) -> None:
            dialog, content, footer = modal_shell(self, "Tạo tài khoản", 520)
            form = QFormLayout(); content.addLayout(form); username, full_name, password, role = QLineEdit(), QLineEdit(), QLineEdit(), QComboBox(); password.setEchoMode(QLineEdit.EchoMode.Password)
            try: role.addItems([item.name for item in asyncio.run(_roles(self.settings))])
            except Exception: role.addItems(["OPERATOR"])
            form.addRow("Tên đăng nhập", username); form.addRow("Họ tên", full_name); form.addRow("Mật khẩu", password); form.addRow("Vai trò", role)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu tài khoản"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_account() -> None:
                if not username.text() or not full_name.text() or not password.text(): show_toast(dialog, "Nhập đủ tên đăng nhập, họ tên và mật khẩu.", "error"); return
                try: asyncio.run(_create_user(self.settings, username.text(), password.text(), full_name.text(), role.currentText())); self.load_users(); dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save.clicked.connect(save_account); dialog.exec()

    def edit_account(self, user) -> None:
            dialog, content, footer = modal_shell(self, "Sửa tài khoản", 520); form = QFormLayout(); content.addLayout(form)
            full_name, password, role, active = QLineEdit(user.full_name), QLineEdit(), QComboBox(), QComboBox(); password.setPlaceholderText("Để trống nếu không đổi")
            password.setEchoMode(QLineEdit.EchoMode.Password)
            try: role.addItems([item.name for item in asyncio.run(_roles(self.settings))])
            except Exception: role.addItem(user.role)
            role.setCurrentText(user.role); active.addItem("Hoạt động", True); active.addItem("Đã khóa", False); active.setCurrentIndex(0 if user.is_active else 1)
            form.addRow("Tên đăng nhập", label(user.username, bold=True)); form.addRow("Họ tên", full_name); form.addRow("Mật khẩu mới", password); form.addRow("Vai trò", role); form.addRow("Trạng thái", active)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_item() -> None:
                try: asyncio.run(_update_user(self.settings, user.id, full_name.text(), role.currentText(), bool(active.currentData()), password.text() or None)); self.load_users(); dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save.clicked.connect(save_item); dialog.exec()

    def delete_account(self, user) -> None:
            if user.id == getattr(self.user, "user_id"):
                show_toast(self, "Không thể xóa tài khoản đang đăng nhập.", "error"); return
            if QMessageBox.question(self, "Xóa tài khoản", f"Xóa mềm tài khoản '{user.username}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_user(self.settings, user.id)); self.load_users()
            except Exception as exc: show_toast(self, str(exc), "error")

    def manage_roles(self) -> None:
            dialog, box, footer = modal_shell(self, "Vai trò và quyền", 600)
            dialog.setMinimumHeight(520)
            box.addWidget(label("Tạo hoặc chỉnh sửa vai trò", bold=True)); selector = QComboBox(); selector.addItem("+ Vai trò mới"); name, description = QLineEdit(), QLineEdit(); name.setPlaceholderText("Tên vai trò, ví dụ: CASHIER"); description.setPlaceholderText("Mô tả vai trò")
            permissions = QListWidget()
            try:
                catalog = asyncio.run(_permissions(self.settings)); role_records = asyncio.run(_roles(self.settings))
                for record in role_records: selector.addItem(record.name, record)
                for code, desc in catalog:
                    item = QListWidgetItem(f"{code} — {desc}"); item.setData(Qt.ItemDataRole.UserRole, code); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Unchecked); permissions.addItem(item)
            except Exception as exc: show_toast(self, str(exc), "error"); return
            def select_role(index: int) -> None:
                record = selector.itemData(index)
                name.setText(record.name if record else ""); description.setText(record.description if record else "")
                selected = record.permission_codes if record else frozenset()
                for i in range(permissions.count()): permissions.item(i).setCheckState(Qt.CheckState.Checked if permissions.item(i).data(Qt.ItemDataRole.UserRole) in selected else Qt.CheckState.Unchecked)
            selector.currentIndexChanged.connect(select_role); box.addWidget(selector); box.addWidget(name); box.addWidget(description); permission_heading = QHBoxLayout(); permission_heading.addWidget(label("Các quyền được cấp", "muted")); permission_heading.addStretch(); add_permission = QPushButton("+ Thêm quyền"); permission_heading.addWidget(add_permission); box.addLayout(permission_heading); box.addWidget(permissions, 1)
            def add_permission_item() -> None:
                code, ok = QInputDialog.getText(dialog, "Thêm quyền", "Mã quyền (ví dụ: report.export):")
                if not ok or not code.strip(): return
                description_text, ok = QInputDialog.getText(dialog, "Thêm quyền", "Mô tả dễ hiểu:")
                if not ok: return
                try:
                    created_code, created_desc = asyncio.run(_create_permission(self.settings, code, description_text))
                    item = QListWidgetItem(f"{created_code} — {created_desc}"); item.setData(Qt.ItemDataRole.UserRole, created_code); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Checked); permissions.addItem(item)
                except Exception as exc: show_toast(dialog, str(exc), "error")
            add_permission.clicked.connect(add_permission_item)
            cancel, save_button = QPushButton("Hủy"), QPushButton("Lưu vai trò"); save_button.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save_button); cancel.clicked.connect(dialog.reject)
            def save() -> None:
                if not name.text().strip(): show_toast(dialog, "Nhập tên vai trò.", "error"); return
                codes = {permissions.item(i).data(Qt.ItemDataRole.UserRole) for i in range(permissions.count()) if permissions.item(i).checkState() == Qt.CheckState.Checked}
                try: asyncio.run(_save_role(self.settings, name.text().strip().upper(), description.text().strip(), codes)); dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save_button.clicked.connect(save); dialog.exec()

