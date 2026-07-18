"""PMQL desktop UI — a cohesive PySide6 dark admin application."""

from __future__ import annotations

import asyncio
from datetime import date

from pmql.application.use_cases.auth.create_user_use_case import CreateUserInput, CreateUserUseCase
from pmql.application.use_cases.auth.login_use_case import LoginInput, LoginUseCase
from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import VehicleEntryInput, VehicleEntryUseCase
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import VehicleExitInput, VehicleExitUseCase
from pmql.application.use_cases.management_ops import UserManagementUseCase, UserUpdateInput
from pmql.application.use_cases.shift_ops.open_shift_use_case import OpenShiftInput, OpenShiftUseCase
from pmql.config import Settings
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.authorization_repository import SQLiteAuthorizationRepository
from pmql.infrastructure.persistence.sqlite.repositories import (
    SQLiteAlertRepository, SQLiteCardRepository, SQLiteFeeRuleRepository,
    SQLiteLaneRepository, SQLiteSessionRepository, SQLiteShiftRepository,
    SQLiteSubscriberRepository, SQLiteUserRepository, SQLiteVehicleRepository,
)
from pmql.infrastructure.security.jwt_token_service import JwtTokenService
from pmql.infrastructure.security.password_hasher import PBKDF2PasswordHasher
from pmql.infrastructure.sync.outbox_writer import SQLiteSyncOutboxWriter

DEFAULT_LANE_ID = "lane-main-in-out"

THEME = """
* { font-family: 'Segoe UI', Arial; font-size: 13px; color: #f8fafc; }
QMainWindow, QWidget#root, QWidget#page { background: #1e1e2f; }
QFrame#sidebar { background: #171724; border-right: 1px solid #303047; }
QFrame#header, QFrame#card, QFrame#panel { background: #27293d; border: 1px solid #353750; border-radius: 10px; }
QFrame#header { border-radius: 0; border-left: 0; border-right: 0; }
QLabel#muted { color: #a3a6b4; }
QLabel#section { color: #85889b; font-size: 10px; font-weight: 700; padding: 12px 14px 5px; }
QLabel#badge { background: #193c2c; color: #70e1a1; border-radius: 10px; padding: 4px 9px; font-size: 10px; font-weight: 700; }
QLabel#metricValue { font-size: 27px; font-weight: 700; color: #ffffff; }
QLabel#metricCaption { color: #a3a6b4; font-size: 11px; }
QLineEdit, QComboBox { color: #f8fafc; background: #202134; border: 1px solid #3a3b56; border-radius: 8px; padding: 9px 11px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #3b82f6; }
QPushButton { background: #363850; color: #ffffff; border: 0; border-radius: 8px; padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: #454866; }
QPushButton#nav { background: transparent; color: #a3a6b4; text-align: left; padding: 11px 14px; }
QPushButton#nav:hover { background: #292a3d; color: white; }
QPushButton#nav[active='true'] { background: #3b82f6; color: white; }
QPushButton#primary { background: #3b82f6; color: white; }
QPushButton#primary:hover { background: #2563eb; }
QPushButton#success { background: #16a36b; color: white; }
QPushButton#danger { background: #e05252; color: white; }
QTableWidget { background: #27293d; alternate-background-color: #222338; color: #f8fafc; border: 1px solid #353750; border-radius: 9px; gridline-color: #303146; selection-background-color: #3b82f6; }
QHeaderView::section { background: #202134; color: #a3a6b4; border: 0; border-bottom: 1px solid #393b52; padding: 11px; font-weight: 700; }
QScrollBar:vertical { background: #1e1e2f; width: 10px; } QScrollBar::handle:vertical { background: #454866; border-radius: 5px; }
"""


def launch(settings: Settings) -> int:
    """Launch UI; all pages share one MainWindow and one QStackedWidget."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication, QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
            QFormLayout, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
            QLineEdit, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
            QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
            QListWidget, QListWidgetItem,
        )
    except ImportError as exc:
        raise RuntimeError('PySide6 is not installed. Run: pip install -e ".[gui]"') from exc

    def label(text: str, name: str = "", bold: bool = False) -> QLabel:
        item = QLabel(text)
        if name: item.setObjectName(name)
        if bold:
            font = item.font(); font.setBold(True); item.setFont(font)
        return item

    class Login(QWidget):
        def __init__(self) -> None:
            super().__init__(); self.setWindowTitle("PMQL Bãi Xe"); self.setMinimumSize(980, 610); self.setStyleSheet(THEME)
            root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
            brand = QFrame(); brand.setStyleSheet("background:#171724;")
            left = QVBoxLayout(brand); left.setContentsMargins(70, 60, 70, 60); left.addStretch()
            mark = label("P", bold=True); mark.setAlignment(Qt.AlignmentFlag.AlignCenter); mark.setFixedSize(58, 58); mark.setStyleSheet("background:#3b82f6;border-radius:16px;font-size:29px;")
            left.addWidget(mark); title = label("PMQL Bãi Xe", bold=True); title.setStyleSheet("font-size:30px;margin-top:18px;"); left.addWidget(title)
            left.addWidget(label("Hệ thống quản lý bãi xe thông minh", "muted")); left.addSpacing(34)
            for line in ("✓ Vận hành làn xe thời gian thực", "✓ Quản lý thuê bao & thẻ RFID", "✓ Báo cáo doanh thu và ca làm việc", "✓ Phân quyền tài khoản vận hành"):
                left.addWidget(label(line)); left.addSpacing(12)
            left.addStretch()
            form_box = QFrame(); form = QVBoxLayout(form_box); form.setContentsMargins(58, 70, 58, 55); form.addStretch()
            h = label("Đăng nhập", bold=True); h.setStyleSheet("font-size:27px;"); form.addWidget(h); form.addWidget(label("Chào mừng bạn quay lại hệ thống PMQL.", "muted")); form.addSpacing(25)
            self.username, self.password = QLineEdit("admin"), QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password); self.password.setPlaceholderText("Mật khẩu")
            fields = QFormLayout(); fields.addRow("Tên đăng nhập", self.username); fields.addRow("Mật khẩu", self.password); form.addLayout(fields); form.addSpacing(18)
            submit = QPushButton("Đăng nhập"); submit.setObjectName("primary"); submit.clicked.connect(self.sign_in); self.password.returnPressed.connect(self.sign_in); form.addWidget(submit)
            self.notice = label("", "muted"); form.addWidget(self.notice); form.addStretch(); form.addWidget(label("Tài khoản mặc định: admin / 123", "muted"))
            root.addWidget(brand, 6); root.addWidget(form_box, 4)

        def sign_in(self) -> None:
            try: result = asyncio.run(_authenticate(settings, self.username.text(), self.password.text()))
            except Exception: self.notice.setText("Không thể đăng nhập. Kiểm tra lại tài khoản hoặc mật khẩu."); return
            self.window = Main(result); self.window.showMaximized(); self.close()

    class Main(QMainWindow):
        def __init__(self, user: object) -> None:
            super().__init__(); self.user = user; self.shift_id: str | None = None; self.nav: dict[str, QPushButton] = {}
            self.setWindowTitle("PMQL Bãi Xe – Quản trị vận hành"); self.setMinimumSize(1180, 720); self.setStyleSheet(THEME)
            root = QWidget(); root.setObjectName("root"); layout = QHBoxLayout(root); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
            layout.addWidget(self.build_sidebar()); right = QWidget(); right_layout = QVBoxLayout(right); right_layout.setContentsMargins(0, 0, 0, 0); right_layout.setSpacing(0)
            right_layout.addWidget(self.build_header()); self.stack = QStackedWidget(); right_layout.addWidget(self.stack); layout.addWidget(right, 1); self.setCentralWidget(root)
            self.pages = {"overview": self.overview_page(), "operations": self.operations_page(), "sessions": self.table_page("Phiên gửi xe", ["Biển số", "Trạng thái", "Vào lúc", "Ra lúc", "Phí"], _session_rows), "shifts": self.table_page("Ca làm việc", ["Nhân viên", "Bắt đầu", "Kết thúc", "Doanh thu", "Trạng thái"], _shift_rows), "subscribers": self.table_page("Quản lý thuê bao", ["Họ tên", "Số điện thoại", "Loại xe", "Hiệu lực đến", "Trạng thái"], _subscriber_rows), "cards": self.table_page("Quản lý thẻ RFID", ["Mã thẻ", "Thuê bao", "Xe", "Trạng thái"], _card_rows), "alerts": self.table_page("Cảnh báo", ["Loại", "Mức độ", "Nội dung", "Thời gian", "Trạng thái"], _alert_rows), "fees": self.fee_page(), "accounts": self.accounts_page()}
            for page in self.pages.values(): self.stack.addWidget(page)
            self.go("overview")

        def build_sidebar(self) -> QWidget:
            side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(250); box = QVBoxLayout(side); box.setContentsMargins(12, 20, 12, 16)
            box.addWidget(label("P  PMQL BÃI XE", bold=True)); box.addWidget(label("Hệ thống quản lý bãi xe", "muted")); box.addSpacing(18)
            groups = [("", [("overview", "▦  Tổng quan"), ("operations", "⚑  Vận hành làn"), ("sessions", "◌  Phiên gửi xe"), ("alerts", "▲  Cảnh báo"), ("shifts", "◴  Ca làm việc")]), ("QUẢN LÝ", [("subscribers", "▣  Thuê bao"), ("cards", "▤  Thẻ xe"), ("fees", "◆  Biểu phí")]), ("HỆ THỐNG", [("accounts", "♙  Tài khoản & phân quyền")])]
            for group, links in groups:
                if group: box.addWidget(label(group, "section"))
                for key, text in links:
                    if key == "accounts" and getattr(self.user, "role") != "ADMIN": continue
                    button = QPushButton(text); button.setObjectName("nav"); button.clicked.connect(lambda _=False, target=key: self.go(target)); box.addWidget(button); self.nav[key] = button
            box.addStretch(); box.addWidget(label("ĐANG ĐĂNG NHẬP", "section")); box.addWidget(label(getattr(self.user, "full_name"), bold=True)); box.addWidget(label(getattr(self.user, "role"), "badge", True)); return side

        def build_header(self) -> QWidget:
            bar = QFrame(); bar.setObjectName("header"); row = QHBoxLayout(bar); row.setContentsMargins(24, 12, 24, 12)
            self.breadcrumb = label("Tổng quan", bold=True); self.breadcrumb.setStyleSheet("font-size:17px;"); row.addWidget(self.breadcrumb); row.addStretch()
            search = QLineEdit(); search.setPlaceholderText("⌕  Tìm kiếm…"); search.setMaximumWidth(285); row.addWidget(search); row.addSpacing(14); row.addWidget(label("● Kết nối", "badge", True)); row.addSpacing(12); row.addWidget(label(f"◉  {getattr(self.user, 'username')}", bold=True)); return bar

        def go(self, key: str) -> None:
            self.stack.setCurrentWidget(self.pages[key]); self.breadcrumb.setText({"overview":"Tổng quan hệ thống", "operations":"Vận hành làn xe", "sessions":"Phiên gửi xe", "shifts":"Ca làm việc", "subscribers":"Quản lý thuê bao", "cards":"Quản lý thẻ xe", "fees":"Quản lý biểu phí", "alerts":"Cảnh báo", "accounts":"Tài khoản & phân quyền"}[key])
            for item_key, button in self.nav.items(): button.setProperty("active", item_key == key); button.style().unpolish(button); button.style().polish(button)
            if key in {"overview", "operations"}: self.refresh_live()

        def page(self) -> tuple[QWidget, QVBoxLayout]:
            page = QWidget(); page.setObjectName("page"); box = QVBoxLayout(page); box.setContentsMargins(28, 24, 28, 24); box.setSpacing(16); return page, box

        def card(self, caption: str, value: str = "—") -> tuple[QFrame, QLabel]:
            frame = QFrame(); frame.setObjectName("card"); box = QVBoxLayout(frame); box.setContentsMargins(18, 16, 18, 16); box.addWidget(label(caption, "metricCaption")); number = label(value, "metricValue", True); box.addWidget(number); return frame, number

        def overview_page(self) -> QWidget:
            page, box = self.page(); title = label("Tổng quan hệ thống", bold=True); title.setStyleSheet("font-size:24px;"); box.addWidget(title); box.addWidget(label("Tình hình vận hành bãi xe hôm nay.", "muted")); grid = QGridLayout(); self.overview_values = []
            for index, caption in enumerate(("XE ĐANG TRONG BÃI", "LƯỢT XE HÔM NAY", "DOANH THU HÔM NAY", "TÀI KHOẢN HOẠT ĐỘNG")):
                frame, value = self.card(caption); grid.addWidget(frame, 0, index); self.overview_values.append(value)
            box.addLayout(grid); panel = QFrame(); panel.setObjectName("panel"); inside = QVBoxLayout(panel); inside.addWidget(label("Xe đang trong bãi", bold=True)); self.live_table = self.make_table(["Biển số", "Trạng thái", "Thời điểm vào", "Làn vào"], 6); inside.addWidget(self.live_table); box.addWidget(panel, 1); return page

        def operations_page(self) -> QWidget:
            page, box = self.page(); top = QHBoxLayout(); top.addWidget(label("Vận hành làn xe", bold=True)); top.addStretch(); self.shift_button = QPushButton("▶  Mở ca làm việc"); self.shift_button.setObjectName("success"); self.shift_button.clicked.connect(self.open_shift); top.addWidget(self.shift_button); box.addLayout(top)
            self.operation_note = label("Chưa mở ca. Mở ca trước khi ghi nhận xe vào.", "muted"); box.addWidget(self.operation_note); grid = QGridLayout(); self.lane_plate = []
            for index, (name, direction) in enumerate((("Làn vào 1", "VÀO"), ("Làn vào 2", "VÀO"), ("Làn ra 1", "RA"), ("Làn ra 2", "RA"))):
                card = QFrame(); card.setObjectName("card"); card_box = QVBoxLayout(card); row = QHBoxLayout(); row.addWidget(label(name, bold=True)); row.addStretch(); row.addWidget(label(direction, "badge", True)); card_box.addLayout(row); card_box.addWidget(label("Camera đang chờ kết nối", "muted")); plate = label("—", "metricValue", True); plate.setAlignment(Qt.AlignmentFlag.AlignCenter); plate.setStyleSheet("background:#202134;border-radius:8px;padding:13px;color:#fbbf24;"); card_box.addWidget(plate); self.lane_plate.append(plate)
                actions = QHBoxLayout(); enter = QPushButton("↪  Vào"); enter.setObjectName("success"); enter.clicked.connect(self.record_entry); exit_button = QPushButton("↩  Ra"); exit_button.setObjectName("danger"); exit_button.clicked.connect(self.record_exit); actions.addWidget(enter); actions.addWidget(exit_button); card_box.addLayout(actions); grid.addWidget(card, index // 2, index % 2)
            box.addLayout(grid); box.addStretch(); return page

        def make_table(self, headers: list[str], minimum_rows: int = 10) -> QTableWidget:
            table = QTableWidget(0, len(headers)); table.setHorizontalHeaderLabels(headers); table.setAlternatingRowColors(True); table.setShowGrid(False); table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); table.verticalHeader().setVisible(False); table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); table.setMinimumHeight(max(220, minimum_rows * 38)); return table

        def table_page(self, title: str, headers: list[str], loader) -> QWidget:
            page, box = self.page(); heading = QHBoxLayout(); h = label(title, bold=True); h.setStyleSheet("font-size:24px;"); heading.addWidget(h); heading.addStretch(); refresh = QPushButton("↻  Làm mới"); heading.addWidget(refresh); box.addLayout(heading); search = QLineEdit(); search.setPlaceholderText("Tìm kiếm trong danh sách…"); box.addWidget(search); table = self.make_table(headers); box.addWidget(table, 1)
            def load() -> None:
                try: rows = asyncio.run(loader(settings))
                except Exception as exc: QMessageBox.warning(self, "Không tải được dữ liệu", str(exc)); return
                table.setRowCount(len(rows))
                for r, values in enumerate(rows):
                    for c, value in enumerate(values): table.setItem(r, c, QTableWidgetItem(str(value)))
                table.resizeColumnsToContents()
            def filter_rows(query: str) -> None:
                for r in range(table.rowCount()): table.setRowHidden(r, bool(query) and query.lower() not in " ".join(table.item(r,c).text().lower() for c in range(table.columnCount()) if table.item(r,c)))
            refresh.clicked.connect(load); search.textChanged.connect(filter_rows); load(); return page

        def fee_page(self) -> QWidget:
            page, box = self.page(); row = QHBoxLayout(); h = label("Quản lý biểu phí", bold=True); h.setStyleSheet("font-size:24px;"); row.addWidget(h); row.addStretch(); row.addWidget(QPushButton("+ Thêm quy tắc")); box.addLayout(row); grid = QGridLayout()
            try: rules = asyncio.run(_fee_rules(settings))
            except Exception: rules = []
            for index, rule in enumerate(rules):
                frame = QFrame(); frame.setObjectName("card"); c = QVBoxLayout(frame); c.addWidget(label(f"◆  {rule.name}", bold=True)); c.addWidget(label("ĐANG ÁP DỤNG" if rule.is_active else "ĐÃ TẮT", "badge", True)); c.addSpacing(8); c.addWidget(label(f"Giá mỗi block: {rule.price_per_block:,} đ")); c.addWidget(label(f"Block: {rule.block_minutes} phút", "muted")); c.addWidget(label(f"Miễn phí: {rule.free_minutes} phút", "muted")); c.addWidget(QPushButton("Chỉnh sửa")); grid.addWidget(frame, index // 3, index % 3)
            if not rules: box.addWidget(label("Chưa có biểu phí.", "muted"))
            box.addLayout(grid); box.addStretch(); return page

        def accounts_page(self) -> QWidget:
            page, box = self.page(); header = QHBoxLayout(); h = label("Tài khoản & phân quyền", bold=True); h.setStyleSheet("font-size:24px;"); header.addWidget(h); header.addStretch(); roles = QPushButton("Vai trò & quyền"); roles.clicked.connect(self.manage_roles); header.addWidget(roles); create = QPushButton("+ Tạo tài khoản"); create.setObjectName("primary"); create.clicked.connect(self.create_account); header.addWidget(create); box.addLayout(header); self.user_table = self.make_table(["Tên đăng nhập", "Họ tên", "Vai trò", "Trạng thái"]); box.addWidget(self.user_table, 1); self.load_users(); return page

        def load_users(self) -> None:
            if not hasattr(self, "user_table"): return
            try: users = asyncio.run(_users(settings))
            except Exception: return
            self.user_table.setRowCount(len(users))
            for r, user in enumerate(users):
                for c, value in enumerate((user.username, user.full_name, user.role, "Hoạt động" if user.is_active else "Đã khóa")): self.user_table.setItem(r, c, QTableWidgetItem(value))

        def create_account(self) -> None:
            dialog = QDialog(self); dialog.setWindowTitle("Tạo tài khoản"); dialog.setStyleSheet(THEME); form = QFormLayout(dialog); username, full_name, password, role = QLineEdit(), QLineEdit(), QLineEdit(), QComboBox(); password.setEchoMode(QLineEdit.EchoMode.Password)
            try: role.addItems([item.name for item in asyncio.run(_roles(settings))])
            except Exception: role.addItems(["OPERATOR"])
            form.addRow("Tên đăng nhập", username); form.addRow("Họ tên", full_name); form.addRow("Mật khẩu", password); form.addRow("Vai trò", role); buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
            if dialog.exec() == QDialog.DialogCode.Accepted and username.text() and full_name.text() and password.text():
                try: asyncio.run(_create_user(settings, username.text(), password.text(), full_name.text(), role.currentText())); self.load_users()
                except Exception as exc: QMessageBox.warning(self, "Không tạo được", str(exc))

        def manage_roles(self) -> None:
            dialog = QDialog(self); dialog.setWindowTitle("Vai trò và quyền"); dialog.setMinimumSize(600, 520); dialog.setStyleSheet(THEME); box = QVBoxLayout(dialog)
            box.addWidget(label("Tạo hoặc chỉnh sửa vai trò", bold=True)); selector = QComboBox(); selector.addItem("+ Vai trò mới"); name, description = QLineEdit(), QLineEdit(); name.setPlaceholderText("Tên vai trò, ví dụ: CASHIER"); description.setPlaceholderText("Mô tả vai trò")
            permissions = QListWidget(); permissions.setStyleSheet("background:#202134;border:1px solid #3a3b56;border-radius:8px;")
            try:
                catalog = asyncio.run(_permissions(settings)); role_records = asyncio.run(_roles(settings))
                for record in role_records: selector.addItem(record.name, record)
                for code, desc in catalog:
                    item = QListWidgetItem(f"{code} — {desc}"); item.setData(Qt.ItemDataRole.UserRole, code); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Unchecked); permissions.addItem(item)
            except Exception as exc: QMessageBox.warning(self, "Không tải được quyền", str(exc)); return
            def select_role(index: int) -> None:
                record = selector.itemData(index)
                name.setText(record.name if record else ""); description.setText(record.description if record else "")
                selected = record.permission_codes if record else frozenset()
                for i in range(permissions.count()): permissions.item(i).setCheckState(Qt.CheckState.Checked if permissions.item(i).data(Qt.ItemDataRole.UserRole) in selected else Qt.CheckState.Unchecked)
            selector.currentIndexChanged.connect(select_role); box.addWidget(selector); box.addWidget(name); box.addWidget(description); box.addWidget(label("Các quyền được cấp", "muted")); box.addWidget(permissions, 1)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save); buttons.rejected.connect(dialog.reject)
            def save() -> None:
                if not name.text().strip(): QMessageBox.warning(dialog, "Thiếu tên", "Nhập tên vai trò."); return
                codes = {permissions.item(i).data(Qt.ItemDataRole.UserRole) for i in range(permissions.count()) if permissions.item(i).checkState() == Qt.CheckState.Checked}
                try: asyncio.run(_save_role(settings, name.text().strip().upper(), description.text().strip(), codes)); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            buttons.accepted.connect(save); box.addWidget(buttons); dialog.exec()

        def open_shift(self) -> None:
            try: self.shift_id = asyncio.run(_open_shift(settings, getattr(self.user, "user_id")))
            except Exception as exc: QMessageBox.warning(self, "Không thể mở ca", str(exc)); return
            self.operation_note.setText("● Ca đang mở — các phiên xe vào sẽ được tính vào ca này."); self.shift_button.setText("✓ Ca đang hoạt động"); self.refresh_live()

        def record_entry(self) -> None:
            if not self.shift_id: QMessageBox.warning(self, "Chưa mở ca", "Hãy mở ca làm việc trước."); return
            plate, ok = QInputDialog.getText(self, "Xe vào", "Biển số xe:");
            if not ok or not plate.strip(): return
            vehicle, ok = QInputDialog.getItem(self, "Loại xe", "Chọn loại xe:", ["motorbike", "car", "truck"], 0, False)
            if not ok: return
            try: asyncio.run(_entry(settings, plate.strip(), vehicle, self.shift_id)); self.refresh_live()
            except Exception as exc: QMessageBox.warning(self, "Không thể ghi xe vào", str(exc))

        def record_exit(self) -> None:
            plate, ok = QInputDialog.getText(self, "Xe ra", "Biển số xe:");
            if not ok or not plate.strip(): return
            try: fee, minutes = asyncio.run(_exit(settings, plate.strip())); QMessageBox.information(self, "Xe ra", f"Phí: {fee:,} VND\nThời gian: {minutes} phút"); self.refresh_live()
            except Exception as exc: QMessageBox.warning(self, "Không thể ghi xe ra", str(exc))

        def refresh_live(self) -> None:
            try: stats = asyncio.run(_stats(settings, self.shift_id))
            except Exception: return
            if hasattr(self, "overview_values"):
                for target, value in zip(self.overview_values, (f"{stats['active']} xe", f"{stats['today_count']} lượt", f"{stats['revenue']:,} đ", str(stats['users']))): target.setText(value)
                self.live_table.setRowCount(len(stats["plates"]))
                for r, plate in enumerate(stats["plates"]):
                    for c, value in enumerate((plate, "Đang gửi", "Hôm nay", "Làn chính")): self.live_table.setItem(r, c, QTableWidgetItem(value))
            if hasattr(self, "lane_plate"):
                for i, item in enumerate(self.lane_plate): item.setText(stats["plates"][0] if i == 0 and stats["plates"] else "—")

    app = QApplication.instance() or QApplication([]); app.setStyle("Fusion"); login = Login(); login.show(); return app.exec()


async def _authenticate(settings: Settings, username: str, password: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await LoginUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher(), JwtTokenService(settings.secret_key, settings.access_token_expire_minutes)).execute(LoginInput(username, password))
    finally: await db.dispose()

async def _open_shift(settings: Settings, user_id: str) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return (await OpenShiftUseCase(SQLiteShiftRepository(session)).execute(OpenShiftInput(settings.branch_id, user_id))).shift_id
    finally: await db.dispose()

async def _entry(settings: Settings, plate: str, vehicle: str, shift_id: str) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            output = await VehicleEntryUseCase(SQLiteSessionRepository(session), SQLiteVehicleRepository(session), SQLiteCardRepository(session), SQLiteFeeRuleRepository(session), SQLiteSubscriberRepository(session), SQLiteLaneRepository(session), MockBarrierController(), SQLiteSyncOutboxWriter(session)).execute(VehicleEntryInput(DEFAULT_LANE_ID, plate_number=plate, vehicle_type=vehicle, shift_id=shift_id)); return output.session_id
    finally: await db.dispose()

async def _exit(settings: Settings, plate: str) -> tuple[int, int]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            output = await VehicleExitUseCase(SQLiteSessionRepository(session), SQLiteCardRepository(session), SQLiteFeeRuleRepository(session), SQLiteSubscriberRepository(session), SQLiteVehicleRepository(session), MockBarrierController(), FeeCalculator(), SQLiteSyncOutboxWriter(session)).execute(VehicleExitInput(DEFAULT_LANE_ID, plate_number=plate)); return output.fee_amount, output.duration_minutes
    finally: await db.dispose()

async def _users(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteUserRepository(session).list_all()
    finally: await db.dispose()

async def _create_user(settings: Settings, username: str, password: str, full_name: str, role: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await CreateUserUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher()).execute(CreateUserInput(settings.branch_id, username, password, full_name, role))
    finally: await db.dispose()

async def _stats(settings: Settings, shift_id: str | None) -> dict[str, object]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            sessions = await SQLiteSessionRepository(session).list_recent(settings.branch_id, 500); users = await SQLiteUserRepository(session).list_all()
        active = [s for s in sessions if s.status == "ACTIVE"]; today = date.today(); closed = [s for s in sessions if s.exit_time and s.exit_time.date() == today]
        return {"active": len(active), "plates": [s.plate_number for s in active if s.plate_number], "today_count": len([s for s in sessions if s.entry_time.date() == today]), "revenue": sum(s.fee_amount for s in closed), "users": len([u for u in users if u.is_active])}
    finally: await db.dispose()

async def _session_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteSessionRepository(session).list_recent(settings.branch_id, 100)
        return [(s.plate_number or "RFID", s.status, s.entry_time.strftime("%d/%m %H:%M"), s.exit_time.strftime("%d/%m %H:%M") if s.exit_time else "—", f"{s.fee_amount:,} đ") for s in rows]
    finally: await db.dispose()

async def _subscriber_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteSubscriberRepository(session).list_all()
        return [(s.full_name, s.phone, s.vehicle_type, s.valid_until.isoformat(), "Hoạt động" if s.is_active else "Đã khóa") for s in rows]
    finally: await db.dispose()

async def _card_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteCardRepository(session).list_all()
        return [(c.rfid_code, c.subscriber_id or "—", c.vehicle_id or "—", "Hoạt động" if c.is_active else "Đã khóa") for c in rows]
    finally: await db.dispose()

async def _shift_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteShiftRepository(session).list_by_branch(settings.branch_id, 100)
        return [(s.operator_id[:8], s.start_time.strftime("%d/%m %H:%M"), s.end_time.strftime("%d/%m %H:%M") if s.end_time else "—", f"{s.total_revenue:,} đ", s.status) for s in rows]
    finally: await db.dispose()

async def _alert_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteAlertRepository(session).list_recent(100)
        return [(a.alert_type, a.severity, a.message, a.created_at.strftime("%d/%m %H:%M"), "Đã xác nhận" if a.is_acknowledged else "Chưa xác nhận") for a in rows]
    finally: await db.dispose()

async def _fee_rules(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteFeeRuleRepository(session).list_all()
    finally: await db.dispose()

async def _roles(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteAuthorizationRepository(session); await repo.ensure_starter_roles(); return await repo.list_roles()
    finally: await db.dispose()

async def _permissions(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteAuthorizationRepository(session).list_permissions()
    finally: await db.dispose()

async def _save_role(settings: Settings, name: str, description: str, codes: set[str]):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteAuthorizationRepository(session).save_role(name, description, codes)
    finally: await db.dispose()
