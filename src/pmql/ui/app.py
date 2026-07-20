"""PMQL desktop UI — a cohesive PySide6 dark admin application."""

from __future__ import annotations

import asyncio
from datetime import date, datetime

from pmql.application.use_cases.auth.create_user_use_case import CreateUserInput, CreateUserUseCase
from pmql.application.use_cases.auth.login_use_case import LoginInput, LoginUseCase
from pmql.application.use_cases.lane_ops.vehicle_entry_use_case import VehicleEntryInput, VehicleEntryUseCase
from pmql.application.use_cases.lane_ops.vehicle_exit_use_case import VehicleExitInput, VehicleExitUseCase
from pmql.application.use_cases.management_ops import FeeRuleInput, FeeRuleManagementUseCase, SubscriberManagementUseCase, SubscriberUpdateInput, UserManagementUseCase, UserUpdateInput, ShiftInput, ShiftManagementUseCase
from pmql.application.use_cases.subscriber_ops.register_subscriber_use_case import RegisterSubscriberInput, RegisterSubscriberUseCase
from pmql.application.use_cases.shift_ops.open_shift_use_case import OpenShiftInput, OpenShiftUseCase
from pmql.application.use_cases.shift_ops.close_shift_use_case import CloseShiftInput, CloseShiftUseCase
from pmql.config import Settings
from pmql.domain.entities.card import Card
from pmql.domain.entities.lane import Lane
from pmql.domain.services.fee_calculator import FeeCalculator
from pmql.infrastructure.hardware.mock_hardware import MockBarrierController
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.authorization_repository import SQLiteAuthorizationRepository
from pmql.infrastructure.persistence.sqlite.vehicle_type_repository import SQLiteVehicleTypeRepository
from pmql.infrastructure.persistence.sqlite.repositories import (
    SQLiteAlertRepository, SQLiteCardRepository, SQLiteFeeRuleRepository,
    SQLiteLaneRepository, SQLiteSessionRepository, SQLiteShiftRepository,
    SQLiteSubscriberRepository, SQLiteUserRepository, SQLiteVehicleRepository,
)
from pmql.infrastructure.security.jwt_token_service import JwtTokenService
from pmql.infrastructure.security.password_hasher import PBKDF2PasswordHasher
from pmql.infrastructure.sync.outbox_writer import SQLiteSyncOutboxWriter
from pmql.ui.components import LIGHT_THEME as THEME, modal_shell

DEFAULT_LANE_ID = "lane-main-in-out"

LEGACY_THEME = """
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
            QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel,
            QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QStackedWidget,
            QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
            QListWidget, QListWidgetItem, QTabWidget, QProgressBar
        )
        from PySide6.QtGui import QIcon, QFont
        from PySide6.QtCore import QSize
    except ImportError as exc:
        raise RuntimeError('PySide6 is not installed. Run: pip install -e ".[gui]"') from exc

    try:
        import qtawesome as qta
        _HAS_QTA = True
    except ImportError:
        _HAS_QTA = False

    # --- Icon button helper ---
    _BTN_ICON_STYLE = (
        "QPushButton { border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; }"
    )
    _BTN_EDIT_STYLE = "QPushButton { background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; } QPushButton:hover { background: #2563eb; }"
    _BTN_DEL_STYLE  = "QPushButton { background: #ef4444; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; } QPushButton:hover { background: #dc2626; }"
    _BTN_PLAIN_STYLE = "QPushButton { background: #64748b; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; } QPushButton:hover { background: #475569; }"

    def icon_btn(icon_name: str, text: str, style: str = _BTN_EDIT_STYLE, size: int = 16, icon_color: str = "white") -> QPushButton:
        """Create a styled icon button using qtawesome icons."""
        btn = QPushButton()
        if _HAS_QTA:
            try:
                ico = qta.icon(icon_name, color=icon_color)
                btn.setIcon(ico)
                btn.setIconSize(QSize(size, size))
                btn.setText(f" {text}")
            except Exception:
                btn.setText(text)
        else:
            btn.setText(text)
        btn.setStyleSheet(style)
        btn.setFixedHeight(30)
        return btn

    def label(text: str, name: str = "", bold: bool = False, style: str = "") -> QLabel:
        item = QLabel(text)
        if name: item.setObjectName(name)
        if bold:
            font = item.font(); font.setBold(True); item.setFont(font)
        if style:
            item.setStyleSheet(style)
        return item

    class Login(QWidget):
        def __init__(self) -> None:
            super().__init__(); self.setWindowTitle("PMQL Bãi Xe"); self.setMinimumSize(980, 610); self.setStyleSheet(THEME)
            root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
            brand = QFrame(); brand.setObjectName("sidebar")
            left = QVBoxLayout(brand); left.setContentsMargins(70, 60, 70, 60); left.addStretch()
            mark = label("P", bold=True); mark.setAlignment(Qt.AlignmentFlag.AlignCenter); mark.setFixedSize(58, 58); mark.setStyleSheet("background:#3b82f6;border-radius:16px;font-size:29px;")
            left.addWidget(mark); title = label("PMQL Bãi Xe", bold=True); title.setStyleSheet("font-size:30px;margin-top:18px;color:#ffffff;"); left.addWidget(title)
            left.addWidget(label("Hệ thống quản lý bãi xe thông minh", "muted")); left.addSpacing(34)
            for line in ("✓ Vận hành làn xe thời gian thực", "✓ Quản lý thuê bao & thẻ RFID", "✓ Báo cáo doanh thu và ca làm việc", "✓ Phân quyền tài khoản vận hành"):
                left.addWidget(label(line)); left.addSpacing(12)
            left.addStretch()
            form_box = QFrame(); form_box.setObjectName("card"); form = QVBoxLayout(form_box); form.setContentsMargins(58, 70, 58, 55); form.addStretch()
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
            try: self.permission_codes = asyncio.run(_role_permissions(settings, getattr(user, "role")))
            except Exception: self.permission_codes = set()
            self.setWindowTitle("PMQL Bãi Xe – Quản trị vận hành"); self.setMinimumSize(1180, 720); self.setStyleSheet(THEME)
            root = QWidget(); root.setObjectName("root"); layout = QHBoxLayout(root); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
            layout.addWidget(self.build_sidebar()); right = QWidget(); right_layout = QVBoxLayout(right); right_layout.setContentsMargins(0, 0, 0, 0); right_layout.setSpacing(0)
            right_layout.addWidget(self.build_header()); self.stack = QStackedWidget(); right_layout.addWidget(self.stack); layout.addWidget(right, 1); self.setCentralWidget(root)
            self.page_factories = {"overview": self.overview_page, "operations": self.operations_page, "sessions": lambda: self.table_page("Phiên gửi xe", ["Biển số", "Trạng thái", "Vào lúc", "Ra lúc", "Phí"], _session_rows), "shifts": self.shift_page, "subscribers": self.subscriber_page, "cards": self.card_page, "alerts": lambda: self.table_page("Cảnh báo", ["Loại", "Mức độ", "Nội dung", "Thời gian", "Trạng thái"], _alert_rows), "fees": self.fee_page, "lanes": self.lane_page, "vehicle_types": self.vehicle_type_page, "accounts": self.accounts_page}
            self.pages = {key: factory() for key, factory in self.page_factories.items()}
            for page in self.pages.values(): self.stack.addWidget(page)
            self.go("overview")

        def build_sidebar(self) -> QWidget:
            side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(250); box = QVBoxLayout(side); box.setContentsMargins(12, 20, 12, 16)
            box.addWidget(label("P  PMQL BÃI XE", bold=True)); box.addWidget(label("Hệ thống quản lý bãi xe", "muted")); box.addSpacing(18)
            groups = [("", [("overview", "▦  Tổng quan"), ("operations", "⚑  Vận hành làn"), ("sessions", "◌  Phiên gửi xe"), ("alerts", "▲  Cảnh báo"), ("shifts", "◴  Ca làm việc")]), ("QUẢN LÝ", [("subscribers", "▣  Thuê bao"), ("cards", "▤  Thẻ xe"), ("fees", "◆  Biểu phí"), ("lanes", "⚙  Cấu hình làn"), ("vehicle_types", "▧  Loại xe")]), ("HỆ THỐNG", [("accounts", "♙  Tài khoản & phân quyền")])]
            for group, links in groups:
                if group: box.addWidget(label(group, "section"))
                required = {"operations": "lane.operate", "sessions": "session.view", "alerts": "alert.manage", "shifts": "shift.manage", "subscribers": "subscriber.manage", "cards": "card.manage", "fees": "fee.manage", "lanes": "lane.view", "vehicle_types": "fee.manage", "accounts": "user.manage"}
                for key, text in links:
                    if key in required and required[key] not in self.permission_codes: continue
                    button = QPushButton(text); button.setObjectName("nav"); button.clicked.connect(lambda _=False, target=key: self.go(target)); box.addWidget(button); self.nav[key] = button
            box.addStretch(); box.addWidget(label("ĐANG ĐĂNG NHẬP", "section")); box.addWidget(label(getattr(self.user, "full_name"), bold=True)); box.addWidget(label(getattr(self.user, "role"), "badge", True)); return side

        def build_header(self) -> QWidget:
            bar = QFrame(); bar.setObjectName("header"); row = QHBoxLayout(bar); row.setContentsMargins(24, 12, 24, 12)
            self.breadcrumb = label("Tổng quan", bold=True); self.breadcrumb.setStyleSheet("font-size:17px;"); row.addWidget(self.breadcrumb); row.addStretch()
            search = QLineEdit(); search.setPlaceholderText("⌕  Tìm kiếm…"); search.setMaximumWidth(285); row.addWidget(search); row.addSpacing(14); row.addWidget(label("● Kết nối", "badge", True)); row.addSpacing(12); row.addWidget(label(f"◉  {getattr(self.user, 'username')}", bold=True)); return bar

        def go(self, key: str) -> None:
            self.stack.setCurrentWidget(self.pages[key]); self.breadcrumb.setText({"overview":"Tổng quan hệ thống", "operations":"Vận hành làn xe", "sessions":"Phiên gửi xe", "shifts":"Ca làm việc", "subscribers":"Quản lý thuê bao", "cards":"Quản lý thẻ xe", "fees":"Quản lý biểu phí", "lanes":"Cấu hình làn xe", "vehicle_types":"Cấu hình loại xe", "alerts":"Cảnh báo", "accounts":"Tài khoản & phân quyền"}[key])
            for item_key, button in self.nav.items(): button.setProperty("active", item_key == key); button.style().unpolish(button); button.style().polish(button)
            if key in {"overview", "operations"}: self.refresh_live()

        def reload_page(self, key: str) -> None:
            """Recreate a data page so CRUD changes are visible immediately."""
            old_page = self.pages[key]
            index = self.stack.indexOf(old_page)
            new_page = self.page_factories[key]()
            self.stack.removeWidget(old_page)
            old_page.deleteLater()
            self.stack.insertWidget(index, new_page)
            self.pages[key] = new_page
            self.go(key)

        def page(self) -> tuple[QWidget, QVBoxLayout]:
            page = QWidget(); page.setObjectName("page"); box = QVBoxLayout(page); box.setContentsMargins(28, 24, 28, 24); box.setSpacing(16); return page, box

        def card(self, caption: str, value: str = "—") -> tuple[QFrame, QLabel]:
            frame = QFrame(); frame.setObjectName("card"); box = QVBoxLayout(frame); box.setContentsMargins(18, 16, 18, 16); box.addWidget(label(caption, "metricCaption")); number = label(value, "metricValue", True); box.addWidget(number); return frame, number

        def overview_page(self) -> QWidget:
            page, box = self.page(); title = label("Tổng quan hệ thống", bold=True); title.setStyleSheet("font-size:24px;"); box.addWidget(title); box.addWidget(label("Tình hình vận hành bãi xe hôm nay.", "muted")); grid = QGridLayout(); self.overview_values = []
            colors = ("#2f66d0", "#159947", "#f06d1c", "#cf3436")
            for index, caption in enumerate(("XE ĐANG TRONG BÃI", "LƯỢT XE HÔM NAY", "DOANH THU HÔM NAY", "CẢNH BÁO CHỜ XỬ LÝ")):
                frame, value = self.card(caption); frame.setStyleSheet(f"background:{colors[index]}; border:0; border-radius:10px;")
                value.setStyleSheet("color:white; font-size:27px; font-weight:800;")
                frame.findChild(QLabel, "metricCaption").setStyleSheet("color:#e8f0ff; font-weight:700;")
                grid.addWidget(frame, 0, index); self.overview_values.append(value)
            box.addLayout(grid); panel = QFrame(); panel.setObjectName("panel"); inside = QVBoxLayout(panel); inside.addWidget(label("Xe đang trong bãi", bold=True)); self.live_table = self.make_table(["Biển số", "Trạng thái", "Thời điểm vào", "Làn vào"], 6); inside.addWidget(self.live_table); box.addWidget(panel, 1); return page

        def operations_page(self) -> QWidget:
            page, box = self.page(); box.setContentsMargins(12, 12, 12, 12); box.setSpacing(12)
            
            # --- Toolbar ---
            toolbar = QHBoxLayout()
            lane_filter = QComboBox(); lane_filter.addItem("— Tất cả làn —")
            try:
                for ln in asyncio.run(_lanes(settings)): lane_filter.addItem(ln.name)
            except Exception: pass
            toolbar.addWidget(lane_filter)
            
            self.shift_status_badge = label("Chưa mở ca", "badge"); self.shift_status_badge.setStyleSheet("background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;")
            toolbar.addWidget(self.shift_status_badge); toolbar.addStretch()
            
            self.shift_button = QPushButton("▶ Mở ca"); self.shift_button.setObjectName("success"); self.shift_button.clicked.connect(self.open_shift)
            toolbar.addWidget(self.shift_button)
            
            refresh_btn = QPushButton("↻"); refresh_btn.setFixedWidth(36)
            toolbar.addWidget(refresh_btn)
            box.addLayout(toolbar)
            
            # --- Sub-Toolbar ---
            sub_toolbar = QHBoxLayout()
            btn_operate = QPushButton("⚑ Vận hành"); btn_operate.setStyleSheet("background: #6366f1; color: white; border: 1px solid #4f46e5;")
            btn_camera = QPushButton("📷 Xem camera")
            btn_finance = QPushButton("📊 Thu/Chi")
            sub_toolbar.addWidget(btn_operate); sub_toolbar.addWidget(btn_camera); sub_toolbar.addWidget(btn_finance); sub_toolbar.addStretch()
            box.addLayout(sub_toolbar)
            
            # --- Metric Bar ---
            metric_bar = QFrame(); metric_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e1b4b, stop:1 #312e81); border-radius: 8px; padding: 10px;")
            mb_layout = QHBoxLayout(metric_bar)
            
            def m_box(val, title, align_right=False):
                w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(10, 0, 10, 0)
                v = label(val); v.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
                t = label(title); t.setStyleSheet("color: #a5b4fc; font-size: 10px; font-weight: bold;")
                if align_right:
                    v.setAlignment(Qt.AlignmentFlag.AlignRight); t.setAlignment(Qt.AlignmentFlag.AlignRight)
                l.addWidget(v); l.addWidget(t)
                return w, v
            
            w1, self.lbl_in_lot = m_box("0 xe", "XE TRONG BÃI")
            w2, self.lbl_rev_today = m_box("0 đ", "DOANH THU HÔM NAY")
            w3, self.lbl_rev_shift = m_box("0 đ", "DOANH THU CA NÀY")
            w4, self.lbl_count_today = m_box("0 lượt", "LƯỢT XE HÔM NAY")
            w5, self.lbl_start_cash = m_box("0 đ", "TIỀN ĐẦU CA", align_right=True)
            
            mb_layout.addWidget(w1); mb_layout.addWidget(w2); mb_layout.addWidget(w3); mb_layout.addWidget(w4); mb_layout.addStretch(); mb_layout.addWidget(w5)
            box.addWidget(metric_bar)
            
            # --- Lane Grid ---
            grid = QGridLayout(); grid.setSpacing(12); self.lane_plate = []
            try: lanes = asyncio.run(_lanes(settings))
            except Exception: lanes = []
            if not lanes: box.addWidget(label("Chưa có làn hoạt động. Hãy tạo làn trong Cấu hình làn.", "muted")); box.addStretch(); return page
            
            for index, lane in enumerate(lanes):
                name, direction = lane.name, {"IN": "VÀO", "OUT": "RA", "BIDIRECTIONAL": "2 CHIỀU"}.get(lane.direction, lane.direction)
                card = QFrame(); card.setObjectName("card"); card_box = QVBoxLayout(card); card_box.setContentsMargins(10, 10, 10, 10)
                
                # Header
                row = QHBoxLayout()
                row.addWidget(label(name, bold=True))
                badge = label(direction, "badge"); badge.setStyleSheet("background: #dcfce7; color: #166534;" if lane.direction == "IN" else "background: #fee2e2; color: #991b1b;")
                row.addWidget(badge)
                wait_badge = label("CHỜ XE", "badge"); wait_badge.setStyleSheet("background: #64748b; color: white;")
                row.addWidget(wait_badge); row.addStretch()
                count_badge = label("0 xe", "badge")
                row.addWidget(count_badge)
                card_box.addLayout(row)
                
                # Status & Plate
                row2 = QHBoxLayout()
                door = label("🚪"); door.setStyleSheet("font-size: 24px; color: #ef4444; border: 2px solid #ef4444; border-radius: 20px; padding: 4px;")
                row2.addWidget(door)
                vbox = QVBoxLayout(); vbox.addWidget(label("● Chờ xe", bold=True))
                plate = label("—"); plate.setAlignment(Qt.AlignmentFlag.AlignCenter); plate.setStyleSheet("background:#fffbeb;border:2px solid #fcd34d;border-radius:4px;font-size:20px;font-weight:bold;color:#b45309;padding:4px;")
                vbox.addWidget(plate); row2.addLayout(vbox)
                card_box.addLayout(row2)
                self.lane_plate.append(plate)
                
                # Camera box
                cam_box = label("📷\nCamera đang chờ..."); cam_box.setAlignment(Qt.AlignmentFlag.AlignCenter); cam_box.setStyleSheet("background: #000000; color: #22c55e; border-radius: 6px; min-height: 120px; font-weight: bold;")
                card_box.addWidget(cam_box)
                
                # Device Badges
                row3 = QHBoxLayout()
                for dev in ["Đầu đọc thẻ", "Camera", "Barrier", "Vân tay"]:
                    b = label(dev); b.setStyleSheet("background: #dcfce7; color: #166534; border-radius: 8px; padding: 2px 6px; font-size: 9px; font-weight: bold;")
                    row3.addWidget(b)
                row3.addStretch()
                card_box.addLayout(row3)
                
                # Inputs
                row4 = QHBoxLayout()
                uid = QLineEdit(); uid.setPlaceholderText("Mã thẻ (UID)"); row4.addWidget(uid)
                pl = QLineEdit(); pl.setPlaceholderText("Biển số"); row4.addWidget(pl)
                card_box.addLayout(row4)
                
                # Action Buttons
                row5 = QHBoxLayout()
                btn_in = QPushButton("→\nVào"); btn_in.setStyleSheet("background: #22c55e; color: white; border-radius: 4px; padding: 8px; font-weight: bold;"); btn_in.clicked.connect(lambda _=False, lane_id=lane.id: self.record_entry(lane_id))
                btn_out = QPushButton("←\nRa"); btn_out.setStyleSheet("background: #ef4444; color: white; border-radius: 4px; padding: 8px; font-weight: bold;"); btn_out.clicked.connect(lambda _=False, lane_id=lane.id: self.record_exit(lane_id))
                btn_issue = QPushButton("💳\nCấp thẻ"); btn_issue.setStyleSheet("background: #f97316; color: white; border-radius: 4px; padding: 8px; font-weight: bold;")
                row5.addWidget(btn_in); row5.addWidget(btn_out); row5.addWidget(btn_issue)
                card_box.addLayout(row5)
                
                # Secondary Buttons
                row6 = QHBoxLayout()
                btn_open = QPushButton("🔓 Mở tay"); btn_open.setStyleSheet("color: #059669; border: 1px solid #10b981;")
                btn_close = QPushButton("🔒 Đóng"); btn_close.setStyleSheet("color: #475569; border: 1px solid #94a3b8;")
                btn_cap = QPushButton("📷 Chụp"); btn_cap.setStyleSheet("color: #0284c7; border: 1px solid #38bdf8;")
                row6.addWidget(btn_open); row6.addWidget(btn_close); row6.addWidget(btn_cap)
                card_box.addLayout(row6)
                
                grid.addWidget(card, index // 3, index % 3)
            
            box.addLayout(grid); box.addStretch(); return page

        def shifts_page(self) -> QWidget:
            page, box = self.page(); box.setContentsMargins(16, 16, 16, 16)
            # Header
            header = QHBoxLayout(); h = label("Quản lý ca làm việc", bold=True); h.setStyleSheet("font-size:24px;")
            header.addWidget(h); header.addStretch()
            btn_open = QPushButton("+ Mở ca mới"); btn_open.setObjectName("primary"); btn_open.clicked.connect(self.open_shift)
            header.addWidget(btn_open); box.addLayout(header)
            
            # Active Shift Panel
            panel = QFrame(); panel.setObjectName("panel"); panel.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e293b, stop:1 #334155); border-radius: 12px; padding: 16px;")
            pbox = QVBoxLayout(panel)
            pbox.addWidget(label("Ca Đang Hoạt Động", "badge", True))
            pgrid = QGridLayout(); pgrid.setContentsMargins(0, 10, 0, 10)
            
            def p_box(val, title, col, is_money=False):
                w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 0, 0)
                v = label(val, bold=True); v.setStyleSheet(f"color: {'#10b981' if is_money else 'white'}; font-size: 20px;")
                t = label(title); t.setStyleSheet("color: #94a3b8; font-size: 11px;")
                l.addWidget(t); l.addWidget(v); pgrid.addWidget(w, 0, col)
            
            if self.shift_id:
                try: stats = asyncio.run(_stats(settings, self.shift_id))
                except Exception: stats = {"revenue": 0, "today_count": 0}
                p_box("Ca đang mở", "LOẠI CA", 0)
                p_box("Tất cả làn", "LÀN HOẠT ĐỘNG", 1)
                p_box("Vừa xong", "GIỜ MỞ CA", 2)
                p_box("0 đ", "SỐ TIỀN ĐẦU CA", 3, True)
                p_box(f"{stats.get('revenue', 0):,} đ", "SỐ DƯ HIỆN TẠI", 4, True)
                p_box(f"{stats.get('today_count', 0)}", "LƯỢT XE", 5)
                p_box(f"{stats.get('revenue', 0):,} đ", "DOANH THU ƯỚC TÍNH", 6, True)
            else:
                pbox.addWidget(label("Không có ca nào đang mở.", "muted"))
            
            pbox.addLayout(pgrid)
            btn_close = QPushButton("⏻ Đóng ca (Bàn giao)"); btn_close.setStyleSheet("background: #ef4444; color: white; border: 0; padding: 10px; font-weight: bold;")
            btn_close.clicked.connect(self.close_shift)
            if not self.shift_id: btn_close.setEnabled(False); btn_close.setStyleSheet("background: #475569; color: #94a3b8; border: 0;")
            
            pbox.addWidget(btn_close); box.addWidget(panel)
            
            # History
            box.addWidget(label("Lịch sử ca làm việc", bold=True))
            table = self.make_table(["Nhân viên", "Bắt đầu", "Kết thúc", "Doanh thu", "Trạng thái"]); box.addWidget(table, 1)
            try: rows = asyncio.run(_shift_rows(settings))
            except Exception: rows = []
            table.setRowCount(len(rows))
            for r, values in enumerate(rows):
                for c, value in enumerate(values): table.setItem(r, c, QTableWidgetItem(str(value)))
            
            return page

        def close_shift(self) -> None:
            if not self.shift_id: return
            dialog, content, footer = modal_shell(self, "Tính toán & Đóng ca", 600)
            
            grid = QGridLayout()
            grid.addWidget(label("Tổng tiền mặt thực tế", "muted"), 0, 0)
            actual_cash = QLineEdit(); actual_cash.setPlaceholderText("0 đ"); grid.addWidget(actual_cash, 1, 0)
            
            grid.addWidget(label("Ghi chú đóng ca", "muted"), 2, 0)
            note = QLineEdit(); note.setPlaceholderText("Ghi chú (bàn giao ca, chênh lệch...)"); grid.addWidget(note, 3, 0)
            content.addLayout(grid)
            
            try: stats = asyncio.run(_stats(settings, self.shift_id))
            except Exception: stats = {"revenue": 0}
            
            summary = QFrame(); summary.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;")
            sv = QVBoxLayout(summary)
            row1 = QHBoxLayout(); row1.addWidget(label("Tiền đầu ca", "muted")); row1.addStretch(); row1.addWidget(label("0 đ", bold=True)); sv.addLayout(row1)
            row2 = QHBoxLayout(); row2.addWidget(label("Doanh thu hệ thống", "muted")); row2.addStretch(); row2.addWidget(label(f"{stats.get('revenue', 0):,} đ", bold=True)); sv.addLayout(row2)
            row3 = QHBoxLayout(); row3.addWidget(label("Tổng tiền dự kiến", "muted")); row3.addStretch(); row3.addWidget(label(f"{stats.get('revenue', 0):,} đ", bold=True)); sv.addLayout(row3)
            row4 = QHBoxLayout(); row4.addWidget(label("Chênh lệch", "muted")); row4.addStretch(); diff_lbl = label("0 đ", bold=True); diff_lbl.setStyleSheet("color: #ef4444;"); row4.addWidget(diff_lbl); sv.addLayout(row4)
            content.addWidget(summary)
            
            def update_diff():
                try: actual = int(actual_cash.text() or 0)
                except ValueError: return
                expected = stats.get('revenue', 0)
                diff = actual - expected
                diff_lbl.setText(f"{diff:,} đ")
                diff_lbl.setStyleSheet("color: #10b981;" if diff >= 0 else "color: #ef4444;")
            
            actual_cash.textChanged.connect(update_diff)
            
            cancel, save = QPushButton("Hủy"), QPushButton("⏻ Đóng ca ngay"); save.setObjectName("danger"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def do_close():
                try:
                    actual = int(actual_cash.text() or 0)
                    asyncio.run(_close_shift(settings, getattr(self.user, "user_id"), actual, note.text()))
                except Exception as exc: QMessageBox.warning(dialog, "Lỗi", str(exc)); return
                self.shift_id = None
                self.shift_status_badge.setText("Chưa mở ca"); self.shift_status_badge.setStyleSheet("background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;")
                self.shift_button.setText("▶ Mở ca")
                self.reload_page("shifts")
                dialog.accept()
            save.clicked.connect(do_close); dialog.exec()

        def make_table(self, headers: list[str], minimum_rows: int = 10, action_col_width: int = 160) -> QTableWidget:
            from PySide6.QtCore import Qt as _Qt
            table = QTableWidget(0, len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.setMinimumHeight(max(220, minimum_rows * 38))
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            hdr = table.horizontalHeader()
            for i in range(len(headers) - 1):
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            # Last column is always the action column - fixed width
            hdr.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(len(headers) - 1, action_col_width)
            table.horizontalHeader().setDefaultAlignment(_Qt.AlignmentFlag.AlignCenter)
            return table

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

        def shift_page(self) -> QWidget:
            page, box = self.page(); heading = QHBoxLayout(); title = label("Quản lý ca làm việc", bold=True); title.setStyleSheet("font-size:24px; color: #1e293b;"); heading.addWidget(title); heading.addStretch(); box.addLayout(heading)
            
            tabs = QTabWidget(); box.addWidget(tabs, 1)
            tabs.setStyleSheet("QTabWidget::pane { border: none; border-top: 1px solid #e0e7f0; top: -1px; } QTabBar::tab { background: transparent; color: #94a3b8; padding: 12px 20px; font-weight: 700; font-size: 14px; border: none; border-bottom: 2px solid transparent; margin-right: 4px; } QTabBar::tab:selected { color: #f97316; border-bottom: 2px solid #f97316; } QTabBar::tab:hover { color: #1e293b; }")

            current_tab = QWidget(); current_layout = QVBoxLayout(current_tab); current_layout.setAlignment(Qt.AlignmentFlag.AlignTop); current_layout.setContentsMargins(0, 20, 0, 0)
            self.current_shift_banner = QFrame(); self.current_shift_banner.setObjectName("card"); self.current_shift_banner.setStyleSheet("#card { background: #ecfdf5; border: 1px solid #d1fae5; border-radius: 12px; padding: 24px; }")
            banner_layout = QVBoxLayout(self.current_shift_banner); banner_layout.setSpacing(12)
            
            banner_top_row = QHBoxLayout()
            banner_left = QVBoxLayout(); banner_left.setSpacing(4)
            
            badge_layout = QHBoxLayout(); badge_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            badge = label("• Ca đang hoạt động", bold=True); badge.setStyleSheet("background: #d1fae5; color: #065f46; border-radius: 12px; padding: 4px 12px; font-size: 12px;")
            badge_layout.addWidget(badge); badge_layout.addStretch()
            banner_left.addLayout(badge_layout)
            
            self.lbl_shift_status = label("Ca làm việc", bold=True); self.lbl_shift_status.setStyleSheet("font-size: 20px; color: #1e293b; margin-top: 8px;")
            self.lbl_shift_desc = label("Bắt đầu: -- | Làn: -- | Đã làm: --"); self.lbl_shift_desc.setStyleSheet("font-size: 13px; color: #64748b; font-weight: bold;")
            banner_left.addWidget(self.lbl_shift_status); banner_left.addWidget(self.lbl_shift_desc)
            
            self.progress_bar = QProgressBar(); self.progress_bar.setFixedHeight(6); self.progress_bar.setTextVisible(False); self.progress_bar.setStyleSheet("QProgressBar { background: #d1fae5; border: none; border-radius: 3px; } QProgressBar::chunk { background: #10b981; border-radius: 3px; }"); self.progress_bar.setValue(50)
            banner_left.addSpacing(4); banner_left.addWidget(self.progress_bar)
            
            banner_top_row.addLayout(banner_left); banner_top_row.addStretch()
            
            self.btn_open_shift = QPushButton("▶ Mở ca làm việc"); self.btn_open_shift.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_open_shift.setStyleSheet("background: #16a34a; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-size: 14px; font-weight: bold;"); self.btn_open_shift.clicked.connect(self.add_shift)
            self.btn_close_shift = QPushButton("■ Đóng ca"); self.btn_close_shift.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_close_shift.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-size: 14px; font-weight: bold;"); self.btn_close_shift.clicked.connect(self.close_shift_dialog); self.btn_close_shift.hide()
            
            btn_layout = QVBoxLayout(); btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            btn_layout.addWidget(self.btn_open_shift); btn_layout.addWidget(self.btn_close_shift)
            banner_top_row.addLayout(btn_layout); banner_layout.addLayout(banner_top_row)
            
            self.stats_grid = QGridLayout(); self.stats_grid.setSpacing(16); self.stats_grid.setContentsMargins(0, 16, 0, 0)
            
            def make_stat_card(num_color, icon_text):
                f = QFrame(); f.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;")
                l = QVBoxLayout(f); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
                num = label("0", bold=True); num.setStyleSheet(f"font-size: 28px; color: {num_color}; padding-bottom: 4px;"); num.setAlignment(Qt.AlignmentFlag.AlignCenter)
                txt = label(icon_text); txt.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;"); txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
                l.addWidget(num); l.addWidget(txt); return f, num
            
            c1, self.val_sessions = make_stat_card("#3b82f6", "🚗 Tổng lượt xe")
            c2, self.val_completed = make_stat_card("#10b981", "✔️ Hoàn thành")
            c3, self.val_parking = make_stat_card("#eab308", "🕒 Đang gửi")
            c4, self.val_revenue = make_stat_card("#16a34a", "💰 Doanh thu ca")
            self.stats_grid.addWidget(c1, 0, 0); self.stats_grid.addWidget(c2, 0, 1)
            self.stats_grid.addWidget(c3, 0, 2); self.stats_grid.addWidget(c4, 0, 3)
            
            current_layout.addWidget(self.current_shift_banner); current_layout.addLayout(self.stats_grid)
            current_layout.addStretch()
            tabs.addTab(current_tab, "▶ Ca hiện tại")

            history_tab = QWidget(); history_layout = QVBoxLayout(history_tab); history_layout.setContentsMargins(0, 20, 0, 0)
            search = QLineEdit(); search.setPlaceholderText("Tìm kiếm trong danh sách…"); history_layout.addWidget(search)
            self.shift_table = self.make_table(["Mã ca", "Nhân viên", "Loại ca", "Làn", "Tiền đầu ca", "Doanh thu", "Bắt đầu", "Kết thúc", "Trạng thái", "Thao tác"]); history_layout.addWidget(self.shift_table, 1)
            search.textChanged.connect(lambda query: [self.shift_table.setRowHidden(r, bool(query) and query.lower() not in " ".join(self.shift_table.item(r,c).text().lower() for c in range(self.shift_table.columnCount()) if self.shift_table.item(r,c))) for r in range(self.shift_table.rowCount())])
            tabs.addTab(history_tab, "🕒 Lịch sử ca")

            self.load_shifts(); return page

        def load_shifts(self) -> None:
            if not hasattr(self, "shift_table"): return
            try: shifts = asyncio.run(_shift_entities(settings))
            except Exception: return
            
            self.shift_table.setRowCount(len(shifts))
            for r, s in enumerate(shifts):
                row_data = [
                    s.id[:8], s.operator_id, s.note or "—", s.lane_id or "Tất cả",
                    f"{s.opening_cash:,} đ", f"{s.total_revenue:,} đ",
                    s.start_time.strftime("%d/%m %H:%M"), s.end_time.strftime("%d/%m %H:%M") if s.end_time else "—", s.status
                ]
                for c, value in enumerate(row_data): self.shift_table.setItem(r, c, QTableWidgetItem(str(value)))
                actions = QWidget(); actions_row = QHBoxLayout(actions); actions_row.setContentsMargins(4, 2, 4, 2)
                edit = QPushButton("Sửa"); edit.clicked.connect(lambda _=False, item=s: self.edit_shift(item)); actions_row.addWidget(edit)
                remove = QPushButton("Xóa"); remove.setObjectName("danger"); remove.clicked.connect(lambda _=False, item=s: self.delete_shift(item)); actions_row.addWidget(remove)
                self.shift_table.setCellWidget(r, 9, actions)
                
            open_shifts = [s for s in shifts if s.status == "OPEN"]
            if open_shifts:
                s = open_shifts[0]
                hours = max(1, int((datetime.now() - s.start_time).total_seconds() / 3600))
                self.lbl_shift_desc.setText(f"Bắt đầu: {s.start_time.strftime('%H:%M:%S %d/%m/%Y')} | Làn: {s.lane_id or 'Tất cả'} | Đã làm: {hours} giờ")
                self.progress_bar.setValue(min(100, int((hours / 8) * 100))) # Assume 8 hour shift
                
                self.val_sessions.setText(str(s.total_sessions))
                self.val_revenue.setText(f"{s.total_revenue:,} đ")
                self.val_completed.setText(str(s.total_sessions)) # Mock logic for completed
                self.val_parking.setText("0") # Mock logic for parking
                
                self.btn_open_shift.hide(); self.btn_close_shift.show(); self.current_shift = s
            else:
                self.lbl_shift_desc.setText("Chưa có ca nào đang mở. Mở ca để bắt đầu ghi nhận dữ liệu.")
                self.progress_bar.setValue(0)
                self.val_sessions.setText("0")
                self.val_revenue.setText("0 đ")
                self.val_completed.setText("0")
                self.val_parking.setText("0")
                
                self.btn_open_shift.show(); self.btn_close_shift.hide(); self.current_shift = None

        def add_shift(self) -> None:
            dialog = QDialog(self); dialog.setWindowTitle("Mở ca làm việc"); dialog.setMinimumWidth(720)
            dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            
            container = QFrame(dialog)
            container.setObjectName("main_container")
            container.setStyleSheet("QFrame#main_container { background: #ffffff; border-radius: 12px; border: 1px solid #94a3b8; }")
            root = QVBoxLayout(dialog); root.setContentsMargins(0, 0, 0, 0); root.addWidget(container)
            
            container_layout = QVBoxLayout(container); container_layout.setContentsMargins(0, 0, 0, 0); container_layout.setSpacing(0)
            
            header = QFrame(); header.setStyleSheet("background: #3b82f6; border-top-left-radius: 12px; border-top-right-radius: 12px;")
            header_row = QHBoxLayout(header); header_row.setContentsMargins(20, 16, 16, 16)
            heading = label("▶ Mở ca làm việc", bold=True); heading.setStyleSheet("font-size:20px; color:white;")
            close_btn = QPushButton("X"); close_btn.setFixedSize(32, 32); close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet("font-family: Arial; font-size: 20px; font-weight: bold; border: none; color: white; background: transparent; padding: 0px; margin: 0px;"); close_btn.clicked.connect(dialog.reject)
            header_row.addWidget(heading); header_row.addStretch(); header_row.addWidget(close_btn)
            container_layout.addWidget(header)
            
            dialog._drag_pos = None
            def header_mousePressEvent(event):
                if event.button() == Qt.MouseButton.LeftButton: dialog._drag_pos = event.globalPosition().toPoint()
            def header_mouseMoveEvent(event):
                if dialog._drag_pos:
                    delta = event.globalPosition().toPoint() - dialog._drag_pos
                    dialog.move(dialog.x() + delta.x(), dialog.y() + delta.y())
                    dialog._drag_pos = event.globalPosition().toPoint()
            def header_mouseReleaseEvent(event): dialog._drag_pos = None
            header.mousePressEvent = header_mousePressEvent
            header.mouseMoveEvent = header_mouseMoveEvent
            header.mouseReleaseEvent = header_mouseReleaseEvent
            
            content = QWidget(); content.setStyleSheet("background: transparent;"); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(24, 24, 24, 24)
            lbl_choose = label("Chọn ca làm việc"); lbl_choose.setStyleSheet("color: #64748b; font-size: 13px; font-weight: bold;"); content_layout.addWidget(lbl_choose); content_layout.addSpacing(10)
            
            cards_layout = QHBoxLayout(); cards_layout.setSpacing(12)
            shift_types = [
                {"id": "sáng", "name": "Ca sáng", "time": "06:00 - 14:00", "hours": "8 tiếng", "icon": "🌅"},
                {"id": "chiều", "name": "Ca chiều", "time": "14:00 - 22:00", "hours": "8 tiếng", "icon": "☀️"},
                {"id": "đêm", "name": "Ca đêm", "time": "22:00 - 06:00", "hours": "8 tiếng", "icon": "🌙"},
                {"id": "đủ", "name": "Ca ngày đủ", "time": "07:00 - 19:00", "hours": "12 tiếng", "icon": "📋"},
            ]
            card_buttons = []
            
            combo_style = "QComboBox { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; font-size: 13px; background: white; color: #1e293b; min-height: 24px; } QComboBox:focus { border: 1px solid #3b82f6; } QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 28px; border-left: none; } QComboBox::down-arrow { image: url(src/pmql/ui/down_arrow.svg); width: 12px; height: 12px; } QLineEdit { padding: 0px; border: none; background: transparent; }"
            
            lane_combo = QComboBox(); lane_combo.addItem("-- Tất cả làn --", None); lane_combo.setStyleSheet(combo_style)
            try:
                for ln in asyncio.run(_lanes(settings)): lane_combo.addItem(ln.name, ln.id)
            except: pass
            
            type_combo = QComboBox(); type_combo.setStyleSheet(combo_style)
            for st in shift_types: type_combo.addItem(f"{st['name']} ({st['time']})", st)
            type_combo.addItem("Khác", {"name": "Khác", "time": "", "hours": ""}); type_combo.setEditable(True)
            
            cash_combo = QComboBox(); cash_combo.setStyleSheet(combo_style); cash_combo.addItems(["Không có tiền đầu ca", "500,000", "1,000,000", "2,000,000"]); cash_combo.setEditable(True)
            note_combo = QComboBox(); note_combo.setStyleSheet(combo_style); note_combo.addItems(["-- Không có ghi chú --", "Bàn giao chìa khóa", "Hệ thống lỗi nhẹ"]); note_combo.setEditable(True)
            
            summary_box = QFrame(); summary_box.setStyleSheet("background: #eff6ff; border-radius: 8px; padding: 16px; margin-top: 10px; border: 1px dashed #93c5fd;")
            summary_layout = QVBoxLayout(summary_box); summary_layout.setSpacing(12)
            lbl_summary_title = label("ℹ️ Thông tin ca sẽ mở", bold=True); lbl_summary_title.setStyleSheet("color: #1e3a8a; font-size: 14px;"); summary_layout.addWidget(lbl_summary_title)
            
            summary_grid = QGridLayout(); summary_grid.setContentsMargins(0, 0, 0, 0); summary_grid.setSpacing(12)
            lbl_sum_type = label(""); lbl_sum_time = label(""); lbl_sum_lane = label(""); lbl_sum_cash = label(""); lbl_sum_note = label("")
            for l in [lbl_sum_type, lbl_sum_time, lbl_sum_lane, lbl_sum_cash, lbl_sum_note]: l.setStyleSheet("color: #1e3a8a; font-size: 13px;")
            summary_grid.addWidget(lbl_sum_type, 0, 0); summary_grid.addWidget(lbl_sum_time, 0, 1)
            summary_grid.addWidget(lbl_sum_lane, 1, 0); summary_grid.addWidget(lbl_sum_cash, 1, 1)
            summary_grid.addWidget(lbl_sum_note, 2, 0, 1, 2); summary_layout.addLayout(summary_grid)
            
            def update_summary():
                st = type_combo.currentData()
                if isinstance(st, dict) and st.get('name') != 'Khác':
                    lbl_sum_type.setText(f"Loại ca: {st.get('icon', '')} <b>{st.get('name', '')}</b>")
                    lbl_sum_time.setText(f"Khung giờ: <b>{st.get('time', '')}</b>")
                else:
                    lbl_sum_type.setText(f"Loại ca: <b>{type_combo.currentText()}</b>")
                    lbl_sum_time.setText("Khung giờ: <b>Tùy chỉnh</b>")
                
                lbl_sum_lane.setText(f"Làn: <b>{lane_combo.currentText()}</b>")
                cash_val = cash_combo.currentText()
                if cash_val == "Không có tiền đầu ca": cash_val = "0 đ"
                elif not cash_val.endswith("đ"): cash_val += " đ"
                lbl_sum_cash.setText(f"Tiền đầu ca: <b>{cash_val}</b>")
                
                n_val = note_combo.currentText()
                if n_val == "-- Không có ghi chú --": n_val = "Không có"
                lbl_sum_note.setText(f"Ghi chú: <b>{n_val}</b>")

            class CardWidget(QFrame):
                def __init__(self, idx, data, parent_dialog):
                    super().__init__(); self.idx = idx; self.parent_dialog = parent_dialog
                    self.setObjectName("card_frame")
                    self.setFixedSize(155, 110); self.setCursor(Qt.CursorShape.PointingHandCursor)
                    l = QVBoxLayout(self); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setSpacing(4)
                    ico = label(data['icon']); ico.setStyleSheet("font-size: 24px; background: transparent; border: none;"); l.addWidget(ico, 0, Qt.AlignmentFlag.AlignHCenter)
                    self.n = label(data['name'], bold=True); self.n.setStyleSheet("font-size: 14px; background: transparent; border: none;"); l.addWidget(self.n, 0, Qt.AlignmentFlag.AlignHCenter)
                    self.t = label(data['time']); self.t.setStyleSheet("font-size: 11px; background: transparent; border: none;"); l.addWidget(self.t, 0, Qt.AlignmentFlag.AlignHCenter)
                    self.h = label(data['hours']); self.h.setStyleSheet("font-size: 11px; background: transparent; font-weight: bold; border: none;"); l.addWidget(self.h, 0, Qt.AlignmentFlag.AlignHCenter)
                def mousePressEvent(self, event): self.parent_dialog.select_card(self.idx)
                
            def select_card(idx):
                for i, btn in enumerate(card_buttons):
                    if i == idx:
                        btn.setStyleSheet("#card_frame { background: #fff7ed; border: 2px solid #f97316; border-radius: 8px; } QLabel { color: #f97316; border: none; }")
                        btn.n.setStyleSheet("font-size: 14px; background: transparent; color: #ea580c; border: none;")
                        btn.t.setStyleSheet("font-size: 11px; background: transparent; color: #ea580c; border: none;")
                        btn.h.setStyleSheet("font-size: 11px; background: transparent; font-weight: bold; color: #ea580c; border: none;")
                    else:
                        btn.setStyleSheet("#card_frame { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; } QLabel { color: #64748b; border: none; }")
                        btn.n.setStyleSheet("font-size: 14px; background: transparent; color: #1e293b; border: none;")
                        btn.t.setStyleSheet("font-size: 11px; background: transparent; color: #64748b; border: none;")
                        btn.h.setStyleSheet("font-size: 11px; background: transparent; font-weight: bold; color: #f97316; border: none;")
                type_combo.setCurrentIndex(idx)
            
            dialog.select_card = select_card
            for i, st in enumerate(shift_types):
                card = CardWidget(i, st, dialog); card_buttons.append(card); cards_layout.addWidget(card)
            content_layout.addLayout(cards_layout); content_layout.addSpacing(24)
            
            form_grid = QGridLayout(); form_grid.setSpacing(16)
            lbl_lane = label("Làn phụ trách"); lbl_lane.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            form_grid.addWidget(lbl_lane, 0, 0); form_grid.addWidget(lane_combo, 1, 0)
            lbl_type = label("Loại ca"); lbl_type.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            form_grid.addWidget(lbl_type, 0, 1); form_grid.addWidget(type_combo, 1, 1)
            lbl_cash = label("Tiền đầu ca (VNĐ)"); lbl_cash.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            form_grid.addWidget(lbl_cash, 2, 0); form_grid.addWidget(cash_combo, 3, 0)
            lbl_note = label("Ghi chú bổ sung"); lbl_note.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            form_grid.addWidget(lbl_note, 2, 1); form_grid.addWidget(note_combo, 3, 1)
            content_layout.addLayout(form_grid); content_layout.addSpacing(16); content_layout.addWidget(summary_box); container_layout.addWidget(content)
            
            lane_combo.currentTextChanged.connect(update_summary); type_combo.currentTextChanged.connect(update_summary)
            cash_combo.currentTextChanged.connect(update_summary); note_combo.currentTextChanged.connect(update_summary)
            select_card(0)
            
            footer = QFrame(); footer.setStyleSheet("background: #f8fafc; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; border-top: 1px solid #e2e8f0;")
            footer_row = QHBoxLayout(footer); footer_row.setContentsMargins(24, 16, 24, 16)
            btn_cancel = QPushButton("Hủy"); btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setStyleSheet("background: #94a3b8; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; font-size: 14px;")
            btn_cancel.clicked.connect(dialog.reject)
            btn_save = QPushButton("▶ Mở ca ngay"); btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_save.setStyleSheet("background: #16a34a; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; font-size: 14px;")
            footer_row.addStretch(); footer_row.addWidget(btn_cancel); footer_row.addWidget(btn_save); container_layout.addWidget(footer)
            
            def save_shift_action() -> None:
                try: 
                    cash_val = int(cash_combo.currentText().replace(",", "").replace(".", "").replace(" Không có tiền đầu ca", "0").replace(" đ", "").strip()) if cash_combo.currentText() and cash_combo.currentText() != "Không có tiền đầu ca" else 0
                    asyncio.run(_open_shift(settings, self.user.user_id, lane_combo.currentData(), type_combo.currentText(), cash_val))
                    self.load_shifts(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Lỗi", str(exc))
            btn_save.clicked.connect(save_shift_action); dialog.exec()
            
        def close_shift_dialog(self) -> None:
            if not getattr(self, "current_shift", None): return
            s = self.current_shift
            
            dialog = QDialog(self); dialog.setWindowTitle("Đóng ca làm việc"); dialog.setMinimumWidth(560)
            dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            
            container = QFrame(dialog); container.setObjectName("main_container")
            container.setStyleSheet("QFrame#main_container { background: #ffffff; border-radius: 12px; border: 1px solid #94a3b8; }")
            root = QVBoxLayout(dialog); root.setContentsMargins(0, 0, 0, 0); root.addWidget(container)
            
            container_layout = QVBoxLayout(container); container_layout.setContentsMargins(0, 0, 0, 0); container_layout.setSpacing(0)
            
            header = QFrame(); header.setStyleSheet("background: #ef4444; border-top-left-radius: 12px; border-top-right-radius: 12px;")
            header_row = QHBoxLayout(header); header_row.setContentsMargins(20, 12, 16, 12)
            heading = label("■ Đóng ca làm việc", bold=True); heading.setStyleSheet("font-size: 18px; color: white;")
            close_btn = QPushButton("X"); close_btn.setFixedSize(32, 32); close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet("font-family: Arial; font-size: 18px; font-weight: bold; border: none; color: white; background: transparent; padding: 0px; margin: 0px;"); close_btn.clicked.connect(dialog.reject)
            header_row.addWidget(heading); header_row.addStretch(); header_row.addWidget(close_btn)
            
            def mousePressEvent(e):
                if e.button() == Qt.MouseButton.LeftButton: dialog.drag_pos = e.globalPosition().toPoint()
            def mouseMoveEvent(e):
                if e.buttons() == Qt.MouseButton.LeftButton and hasattr(dialog, 'drag_pos'):
                    dialog.move(dialog.pos() + e.globalPosition().toPoint() - dialog.drag_pos); dialog.drag_pos = e.globalPosition().toPoint()
            header.mousePressEvent = mousePressEvent; header.mouseMoveEvent = mouseMoveEvent
            container_layout.addWidget(header)
            
            content = QVBoxLayout(); content.setContentsMargins(0, 0, 0, 0); content.setSpacing(16)
            
            summary_layout = QHBoxLayout(); summary_layout.setContentsMargins(24, 16, 24, 0); summary_layout.setSpacing(12)
            def make_summary(val, val_color, lbl_text, border_color, bg_color):
                w = QFrame(); w.setStyleSheet(f"background: {bg_color}; border: 1px solid {border_color}; border-radius: 6px;")
                l = QVBoxLayout(w); l.setContentsMargins(12, 16, 12, 16)
                v = label(str(val), bold=True); v.setStyleSheet(f"color: {val_color}; font-size: 20px; border: none; background: transparent;"); v.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t = label(lbl_text); t.setStyleSheet("color: #64748b; font-size: 13px; border: none; background: transparent;"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
                l.addWidget(v); l.addWidget(t)
                return w
                
            hours = max(1, int((datetime.now() - s.start_time).total_seconds() / 3600))
            mins = int((datetime.now() - s.start_time).total_seconds() % 3600 // 60)
            hours_text = f"{hours}g {mins}p"
            summary_layout.addWidget(make_summary(s.total_sessions, "#16a34a", "Lượt xe", "#bbf7d0", "#f0fdf4"))
            summary_layout.addWidget(make_summary(hours_text, "#2563eb", "Thời gian ca", "#bfdbfe", "#eff6ff"))
            summary_layout.addWidget(make_summary(f"{s.total_revenue:,} đ", "#eab308", "Doanh thu", "#fef08a", "#fefce8"))
            content.addLayout(summary_layout)
            
            form = QFormLayout(); form.setContentsMargins(24, 8, 24, 0); form.setSpacing(12)
            combo_style = "QComboBox { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; font-size: 13px; background: white; color: #1e293b; min-height: 24px; } QComboBox:focus { border: 1px solid #f97316; } QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 28px; border-left: none; } QComboBox::down-arrow { image: url(src/pmql/ui/down_arrow.svg); width: 12px; height: 12px; }"
            input_style = "QLineEdit { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; font-size: 13px; background: white; color: #1e293b; min-height: 24px; } QLineEdit:focus { border: 1px solid #f97316; }"
            
            lbl_cash = label("Tiền mặt thực tế cuối ca"); lbl_cash.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            closing_cash = QComboBox(); closing_cash.setStyleSheet(combo_style)
            closing_cash.addItems([f"{s.opening_cash + s.total_revenue:,} đ", "0 đ", "Nhập số tiền khác..."])
            
            custom_cash = QLineEdit(); custom_cash.setPlaceholderText("Nhập số tiền VNĐ"); custom_cash.setStyleSheet(input_style); custom_cash.hide()
            
            lbl_note = label("Ghi chú bàn giao"); lbl_note.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            close_note = QComboBox(); close_note.setEditable(True); close_note.setStyleSheet(combo_style)
            close_note.addItems(["-- Không có ghi chú --"])
            
            form.addRow(lbl_cash); form.addRow(closing_cash); form.addRow(custom_cash); form.addRow(lbl_note); form.addRow(close_note)
            content.addLayout(form)
            
            recon_box = QFrame(); recon_box.setObjectName("recon_box"); recon_box.setStyleSheet("#recon_box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; margin: 16px 24px 8px 24px; }")
            recon_layout = QVBoxLayout(recon_box); recon_layout.setContentsMargins(16, 16, 16, 16); recon_layout.setSpacing(12)
            
            lbl_recon = label("Đối chiếu thu chi", bold=True); lbl_recon.setStyleSheet("color: #64748b; font-size: 14px; border: none; background: transparent;")
            recon_layout.addWidget(lbl_recon)
            
            def make_recon_row(left_text, right_val, right_color, is_bold_left=False):
                r = QHBoxLayout(); r.setContentsMargins(0, 0, 0, 0)
                l = label(left_text, bold=is_bold_left)
                l_color = "#1e293b" if is_bold_left else "#475569"
                l.setStyleSheet(f"color: {l_color}; font-size: 13px; border: none; background: transparent;")
                
                v = label(right_val, bold=True)
                v.setStyleSheet(f"color: {right_color}; font-size: 14px; text-decoration: underline; border: none; background: transparent;")
                v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                
                r.addWidget(l); r.addStretch(); r.addWidget(v)
                return r, v
            
            row1, val_opening = make_recon_row("Tiền đầu ca:", f"{s.opening_cash:,} đ", "#1e293b")
            row2, val_revenue = make_recon_row("Doanh thu ca:", f"{s.total_revenue:,} đ", "#16a34a")
            row3, val_actual = make_recon_row("Tiền cuối ca thực tế:", "0 đ", "#1e293b")
            
            recon_layout.addLayout(row1); recon_layout.addLayout(row2); recon_layout.addLayout(row3)
            
            line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("border-bottom: 1px solid #e2e8f0; margin: 4px 0px; background: transparent;")
            recon_layout.addWidget(line)
            
            row4, val_diff = make_recon_row("Chênh lệch:", f"{-s.opening_cash - s.total_revenue:,} đ", "#ef4444", True)
            recon_layout.addLayout(row4)
            content.addWidget(recon_box)
            container_layout.addLayout(content)
            
            def update_recon(*_):
                try: 
                    txt = closing_cash.currentText()
                    if txt == "Nhập số tiền khác...":
                        txt = custom_cash.text()
                    txt = txt.replace(",", "").replace(".", "").replace(" đ", "").strip()
                    actual = int(txt) if txt else 0
                except: actual = 0
                expected = s.opening_cash + s.total_revenue
                diff = actual - expected
                val_actual.setText(f"{actual:,} đ")
                val_diff.setText(f"{diff:,} đ")
                if diff < 0: val_diff.setStyleSheet("color: #ef4444; font-size: 14px; text-decoration: underline; border: none; background: transparent;")
                else: val_diff.setStyleSheet("color: #16a34a; font-size: 14px; text-decoration: underline; border: none; background: transparent;")
            
            def on_combo_change(text):
                if text == "Nhập số tiền khác...": custom_cash.show(); custom_cash.setFocus()
                else: custom_cash.hide(); custom_cash.clear()
                update_recon()
            
            closing_cash.currentTextChanged.connect(on_combo_change)
            custom_cash.textChanged.connect(update_recon)
            update_recon()
            
            footer = QFrame(); footer.setStyleSheet("background: white; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
            footer_row = QHBoxLayout(footer); footer_row.setContentsMargins(24, 16, 24, 24)
            cancel = QPushButton("Hủy"); cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel.setStyleSheet("background: #6b7280; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; font-size: 14px;")
            cancel.clicked.connect(dialog.reject)
            save = QPushButton("■ Xác nhận đóng ca"); save.setCursor(Qt.CursorShape.PointingHandCursor)
            save.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 6px; padding: 10px 24px; font-weight: bold; font-size: 14px;")
            footer_row.addStretch(); footer_row.addWidget(cancel); footer_row.addWidget(save); footer_row.addStretch()
            container_layout.addWidget(footer)
            
            def save_shift() -> None:
                try: 
                    txt = closing_cash.currentText()
                    if txt == "Nhập số tiền khác...":
                        txt = custom_cash.text()
                    txt = txt.replace(",", "").replace(".", "").replace(" Không có tiền mặt", "0").replace(" đ", "").strip()
                    cash_val = int(txt) if txt else 0
                    note_txt = close_note.currentText().replace("-- Không có ghi chú --", "").strip()
                    asyncio.run(_close_shift(settings, s.operator_id, cash_val, note_txt))
                    self.load_shifts(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Lỗi", str(exc))
            save.clicked.connect(save_shift); dialog.exec()

        def edit_shift(self, shift) -> None:
            dialog, content, footer = modal_shell(self, "Sửa ca làm việc", 560); form = QFormLayout(); content.addLayout(form)
            operator_id, start_time = QComboBox(), QLineEdit()
            try:
                for u in asyncio.run(_users(settings)):
                    operator_id.addItem(f"{u.full_name} ({u.username})", u.id)
                    if u.id == shift.operator_id: operator_id.setCurrentIndex(operator_id.count() - 1)
            except Exception: pass
            start_time.setText(shift.start_time.strftime("%Y-%m-%d %H:%M:%S"))
            form.addRow("Tài khoản NV *", operator_id); form.addRow("Bắt đầu * (YYYY-MM-DD HH:MM:SS)", start_time)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_shift() -> None:
                try: 
                    st = datetime.strptime(start_time.text().strip(), "%Y-%m-%d %H:%M:%S")
                    inp = ShiftInput(settings.branch_id, operator_id.currentData() or shift.operator_id, st, shift.end_time, shift.total_sessions, shift.total_revenue, shift.status)
                    asyncio.run(_update_shift(settings, shift.id, inp)); self.load_shifts(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_shift); dialog.exec()

        def delete_shift(self, shift) -> None:
            if QMessageBox.question(self, "Xóa ca", f"Xóa vĩnh viễn ca làm việc này?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_shift(settings, shift.id)); self.load_shifts()
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))

        def show_fee_history(self):
            dialog, content, footer = modal_shell(self, "Lịch sử các quy tắc phí", 800)
            from PySide6.QtGui import QColor as _QColor
            hist_tbl = self.make_table(
                ["Quy tắc", "Loại xe", "Giá/block", "Block", "Miễn phí", "Trần/ngày", "Trạng thái"],
                action_col_width=130
            )
            try:
                snap_rules = asyncio.run(_fee_rules(settings))
                snap_names = asyncio.run(_vehicle_name_map(settings))
                hist_tbl.setRowCount(len(snap_rules))
                for ri, sr in enumerate(snap_rules):
                    vals = (
                        sr.name,
                        snap_names.get(sr.vehicle_type, sr.vehicle_type),
                        f"{sr.price_per_block:,} đ",
                        f"{sr.block_minutes} phút",
                        f"{sr.free_minutes} phút",
                        f"{sr.day_max:,} đ" if sr.day_max else "--",
                    )
                    for ci, val in enumerate(vals):
                        itm = QTableWidgetItem(val)
                        itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        hist_tbl.setItem(ri, ci, itm)
                    status_itm = QTableWidgetItem(
                        "Đang áp dụng" if sr.is_active else "Đã tắt"
                    )
                    status_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    status_itm.setForeground(
                        _QColor("#166534" if sr.is_active else "#94a3b8")
                    )
                    hist_tbl.setItem(ri, 6, status_itm)
            except Exception:
                pass
            content.addWidget(hist_tbl)
            close = QPushButton("Đóng"); close.clicked.connect(dialog.reject)
            footer.addStretch(); footer.addWidget(close)
            dialog.exec()

        def show_fee_history(self):
            dialog, content, footer = modal_shell(self, "Lịch sử các quy tắc phí", 800)
            from PySide6.QtGui import QColor as _QColor
            hist_tbl = self.make_table(
                ["Quy tắc", "Loại xe", "Giá/block", "Block", "Miễn phí", "Trần/ngày", "Trạng thái"],
                action_col_width=130
            )
            try:
                snap_rules = asyncio.run(_fee_rules(settings))
                snap_names = asyncio.run(_vehicle_name_map(settings))
                hist_tbl.setRowCount(len(snap_rules))
                for ri, sr in enumerate(snap_rules):
                    vals = (
                        sr.name,
                        snap_names.get(sr.vehicle_type, sr.vehicle_type),
                        f"{sr.price_per_block:,} đ",
                        f"{sr.block_minutes} phút",
                        f"{sr.free_minutes} phút",
                        f"{sr.day_max:,} đ" if sr.day_max else "--",
                    )
                    for ci, val in enumerate(vals):
                        itm = QTableWidgetItem(val)
                        itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        hist_tbl.setItem(ri, ci, itm)
                    status_itm = QTableWidgetItem(
                        "Đang áp dụng" if sr.is_active else "Đã tắt"
                    )
                    status_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    status_itm.setForeground(
                        _QColor("#166534" if sr.is_active else "#94a3b8")
                    )
                    hist_tbl.setItem(ri, 6, status_itm)
            except Exception:
                pass
            content.addWidget(hist_tbl)
            close = QPushButton("Đóng"); close.clicked.connect(dialog.reject)
            footer.addStretch(); footer.addWidget(close)
            dialog.exec()

        def fee_page(self) -> QWidget:
            page, box = self.page()
            
            # Header
            hrow = QHBoxLayout()
            hist_btn = icon_btn("fa5s.history", "Lịch sử thay đổi", "QPushButton { background: white; color: #64748b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; } QPushButton:hover { background: #f1f5f9; }", icon_color="#64748b")
            hist_btn.clicked.connect(self.show_fee_history)
            hrow.addWidget(hist_btn); hrow.addStretch()
            
            add_btn = icon_btn("fa5s.plus", "Thêm quy tắc phí", _BTN_EDIT_STYLE.replace("#3b82f6", "#f97316"))
            add_btn.clicked.connect(self.add_fee_rule)
            hrow.addWidget(add_btn)
            box.addLayout(hrow)

            # Grid of rules
            try:
                rules = asyncio.run(_fee_rules(settings))
                vehicle_names = asyncio.run(_vehicle_name_map(settings))
            except Exception:
                rules = []; vehicle_names = {}

            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            grid_w = QWidget(); grid = QGridLayout(grid_w)
            grid.setSpacing(14); grid.setAlignment(Qt.AlignmentFlag.AlignTop)

            VICONS = {"xe_may": "🛵", "o_to": "🚗", "xe_dap": "🚲", "xe_tai": "🚚"}

            for index, rule in enumerate(rules):
                f = QFrame(); f.setObjectName("fee_card")
                is_active = rule.is_active
                border_color = "#facc15" if is_active else "#e2e8f0"
                f.setStyleSheet(
                    f"QFrame#fee_card {{ background: white; border: 1px solid {border_color};"
                    f" border-radius: 8px; }}"
                )
                c = QVBoxLayout(f); c.setSpacing(12); c.setContentsMargins(16, 14, 16, 14)

                # Title row
                t_row = QHBoxLayout()
                vicon = VICONS.get(rule.vehicle_type, "🚗")
                name_lbl = label(f"{vicon} {rule.name}", bold=True)
                name_lbl.setStyleSheet("font-size:14px; color:#1e293b;")
                t_row.addWidget(name_lbl); t_row.addStretch()

                if is_active:
                    badge = label("Đang áp dụng")
                    badge.setStyleSheet(
                        "background:#fef08a; color:#854d0e; border-radius:4px;"
                        " padding:2px 8px; font-size:11px; font-weight:bold;"
                    )
                    t_row.addWidget(badge)
                c.addLayout(t_row)
                
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color: #e2e8f0;"); c.addWidget(sep)

                # Stats grid (2 columns)
                sg = QGridLayout(); sg.setHorizontalSpacing(30); sg.setVerticalSpacing(10)

                def _stat_row(r_idx, col_idx, lbl_text, val_text, val_color="#1e293b"):
                    lbl = label(lbl_text, "muted"); lbl.setStyleSheet("color:#64748b; font-size:12px; font-weight:bold;")
                    val = label(val_text, bold=True); val.setStyleSheet(f"font-size:13px; color:{val_color};")
                    sg.addWidget(lbl, r_idx, col_idx * 2)
                    sg.addWidget(val, r_idx, col_idx * 2 + 1)
                    sg.setAlignment(val, Qt.AlignmentFlag.AlignRight)

                _stat_row(0, 0, "Giá/block", f"{rule.price_per_block:,} đ", "#16a34a")
                _stat_row(0, 1, "Block", f"{rule.block_minutes} phút")
                
                day_max_txt = f"{rule.day_max:,} đ" if rule.day_max else "Không giới hạn"
                _stat_row(1, 0, "Trần/ngày", day_max_txt)
                _stat_row(1, 1, "Miễn phí", f"{rule.free_minutes} phút")
                
                if rule.night_surcharge:
                    _stat_row(2, 1, "Phụ thu đêm", f"{rule.night_surcharge:,} đ")
                    
                c.addLayout(sg)
                
                sep2_f = QFrame(); sep2_f.setFrameShape(QFrame.Shape.HLine); sep2_f.setStyleSheet("color: #e2e8f0;"); c.addWidget(sep2_f)

                # Actions row (Edit and Delete)
                a_row = QHBoxLayout(); a_row.setContentsMargins(0, 0, 0, 0)
                edit_btn = icon_btn("fa5s.edit", "Sửa", "QPushButton { color: #3b82f6; background: transparent; border: 1px solid #bfdbfe; border-radius: 6px; padding: 6px 12px; font-weight: bold; } QPushButton:hover { background: #eff6ff; }", icon_color="#3b82f6")
                del_btn = icon_btn("fa5s.trash-alt", "", "QPushButton { color: #ef4444; background: transparent; border: 1px solid #fecaca; border-radius: 6px; padding: 6px 10px; font-weight: bold; } QPushButton:hover { background: #fef2f2; }", icon_color="#ef4444")
                
                edit_btn.clicked.connect(lambda _=False, item=rule: self.edit_fee_rule(item))
                del_btn.clicked.connect(lambda _=False, item=rule: self.delete_fee_rule(item))

                a_row.addWidget(edit_btn, 1) # Edit button expands
                a_row.addWidget(del_btn)
                c.addLayout(a_row)

                grid.addWidget(f, index // 3, index % 3)

            scroll.setWidget(grid_w); box.addWidget(scroll, 1)

            # Fee Calculator
            calc_frame = QFrame()
            calc_frame.setObjectName("calc_frame")
            calc_frame.setStyleSheet("QFrame#calc_frame { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
            calc_layout = QVBoxLayout(calc_frame)
            calc_layout.setContentsMargins(20, 16, 20, 16)
            
            calc_title = label("🧮 Tính phí thử", bold=True)
            calc_title.setStyleSheet("color: #d97706; font-size: 14px;")
            calc_layout.addWidget(calc_title)
            
            sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
            sep3.setStyleSheet("color: #e2e8f0;"); calc_layout.addWidget(sep3)

            cg = QGridLayout(); cg.setSpacing(16)
            cg.addWidget(label("Loại xe", "muted"), 0, 0)
            calc_vehicle = QComboBox(); self.fill_vehicle_combo(calc_vehicle)
            cg.addWidget(calc_vehicle, 1, 0)

            from PySide6.QtWidgets import QDateTimeEdit as _DTE
            from PySide6.QtCore import QDateTime as _QDT

            cg.addWidget(label("Giờ vào", "muted"), 0, 1)
            dt_in = _DTE(_QDT.currentDateTime().addSecs(-3600))
            dt_in.setDisplayFormat("dd/MM/yyyy HH:mm"); dt_in.setCalendarPopup(True)
            cg.addWidget(dt_in, 1, 1)

            cg.addWidget(label("Giờ ra", "muted"), 0, 2)
            dt_out = _DTE(_QDT.currentDateTime())
            dt_out.setDisplayFormat("dd/MM/yyyy HH:mm"); dt_out.setCalendarPopup(True)
            cg.addWidget(dt_out, 1, 2)

            calc_btn2 = QPushButton("Tính phí")
            calc_btn2.setStyleSheet("QPushButton { color: #f97316; background: transparent; border: 1px solid #fdba74; border-radius: 6px; padding: 8px 24px; font-weight: bold; } QPushButton:hover { background: #fff7ed; }")
            cg.addWidget(calc_btn2, 1, 3)
            calc_layout.addLayout(cg)
            
            # Result Label
            result_lbl = label("")
            result_lbl.setStyleSheet("color: #1e293b; font-size: 13px;")
            result_lbl.setVisible(False)
            calc_layout.addWidget(result_lbl)

            def do_calc():
                try:
                    from pmql.domain.services.fee_calculator import FeeCalculator as _FC
                    v_code = calc_vehicle.currentData()
                    all_rules = asyncio.run(_fee_rules(settings))
                    active_rules = [r for r in all_rules if r.is_active and r.vehicle_type == v_code]
                    if not active_rules:
                        result_lbl.setStyleSheet("color: #ef4444; font-size: 13px;")
                        result_lbl.setText("Không tìm thấy quy tắc phí nào đang áp dụng cho loại xe này.")
                    else:
                        rule_c = active_rules[0]
                        entry = dt_in.dateTime().toPython()
                        exit_ = dt_out.dateTime().toPython()
                        minutes = max(0, int((exit_ - entry).total_seconds() / 60))
                        calc_obj = _FC(rule_c)
                        fee = calc_obj.calculate(entry, exit_)
                        hours, mins = divmod(minutes, 60)
                        
                        result_lbl.setStyleSheet("color: #16a34a; font-size: 14px; font-weight: bold;")
                        result_lbl.setText(f"Tổng phí: {fee:,} đ (Áp dụng: {rule_c.name} - Thời gian gửi: {hours} giờ {mins} phút)")
                    result_lbl.setVisible(True)
                except Exception as exc:
                    result_lbl.setStyleSheet("color: #ef4444; font-size: 13px;")
                    result_lbl.setText(f"Lỗi: {exc}")
                    result_lbl.setVisible(True)

            calc_btn2.clicked.connect(do_calc)

            box.addWidget(calc_frame)
            return page

        def add_fee_rule(self) -> None:
            dialog, content, footer = modal_shell(self, "Thêm quy tắc phí", 620); form = QFormLayout(); content.addLayout(form)
            name, vehicle, block, price, free, surcharge, maximum = QLineEdit(), QComboBox(), QLineEdit("60"), QLineEdit("5000"), QLineEdit("0"), QLineEdit("0"), QLineEdit(); self.fill_vehicle_combo(vehicle)
            
            status_cb = QComboBox()
            status_cb.addItems(["Đang áp dụng", "Đã tắt"])
            
            form.addRow("Tên quy tắc *", name); form.addRow("Loại xe", vehicle); form.addRow("Block tính (phút)", block); form.addRow("Giá mỗi block (VND)", price); form.addRow("Trần/ngày (VND)", maximum); form.addRow("Phụ thu đêm (VND)", surcharge); form.addRow("Miễn phí (phút đầu)", free); form.addRow("Trạng thái", status_cb)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_rule() -> None:
                try:
                    is_active_val = (status_cb.currentText() == "Đang áp dụng")
                    asyncio.run(_create_fee_rule(settings, name.text(), vehicle.currentData(), int(block.text()), int(price.text()), int(free.text()), int(surcharge.text()), int(maximum.text()) if maximum.text() else None, is_active_val)); dialog.accept(); self.reload_page("fees")
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_rule); dialog.exec()

        def edit_fee_rule(self, rule) -> None:
            dialog, content, footer = modal_shell(self, "Sửa quy tắc phí", 560); form = QFormLayout(); content.addLayout(form)
            name, vehicle, price, block, free, surcharge, maximum = QLineEdit(rule.name), QComboBox(), QLineEdit(str(rule.price_per_block)), QLineEdit(str(rule.block_minutes)), QLineEdit(str(rule.free_minutes)), QLineEdit(str(rule.night_surcharge or 0)), QLineEdit(str(rule.day_max or "")); self.fill_vehicle_combo(vehicle); vehicle.setCurrentIndex(max(0, vehicle.findData(rule.vehicle_type)))
            
            status_cb = QComboBox()
            status_cb.addItems(["Đang áp dụng", "Đã tắt"])
            status_cb.setCurrentText("Đang áp dụng" if rule.is_active else "Đã tắt")
            
            form.addRow("Tên quy tắc", name); form.addRow("Loại xe", vehicle); form.addRow("Giá/block", price); form.addRow("Block (phút)", block); form.addRow("Trần/ngày", maximum); form.addRow("Phụ thu đêm", surcharge); form.addRow("Miễn phí (phút đầu)", free); form.addRow("Trạng thái", status_cb)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_rule() -> None:
                try: 
                    is_active_val = (status_cb.currentText() == "Đang áp dụng")
                    asyncio.run(_update_fee_rule(settings, rule.id, name.text(), vehicle.currentData(), int(block.text()), int(price.text()), int(free.text()), int(surcharge.text()), int(maximum.text()) if maximum.text() else None, is_active_val)); dialog.accept(); self.reload_page("fees")
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_rule); dialog.exec()

        def delete_fee_rule(self, rule) -> None:
            if QMessageBox.question(self, "Xóa biểu phí", f"Xóa mềm quy tắc '{rule.name}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_fee_rule(settings, rule.id)); self.reload_page("fees")
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))
        def subscriber_page(self) -> QWidget:
            page, box = self.page(); row = QHBoxLayout(); title = label("Quản lý thuê bao", bold=True); title.setStyleSheet("font-size:24px;"); row.addWidget(title); row.addStretch(); add = QPushButton("+ Thêm thuê bao"); add.setObjectName("primary"); add.clicked.connect(self.add_subscriber); row.addWidget(add); box.addLayout(row)
            self.subscriber_table = self.make_table(["Họ tên", "Số điện thoại", "CMND/CCCD", "Phương tiện đăng ký", "Hiệu lực đến", "Trạng thái", "Thao tác"], action_col_width=210); box.addWidget(self.subscriber_table, 1); self.load_subscribers(); return page

        def card_page(self) -> QWidget:
            page, box = self.page(); row = QHBoxLayout(); title = label("Quản lý thẻ RFID", bold=True); title.setStyleSheet("font-size:24px;"); row.addWidget(title); row.addStretch(); add = QPushButton("+ Thêm thẻ"); add.setObjectName("primary"); add.clicked.connect(self.add_card); row.addWidget(add); box.addLayout(row)
            self.card_table = self.make_table(["Mã thẻ (UID)", "Loại thẻ", "Thuê bao", "Trạng thái", "Thao tác"], action_col_width=210); box.addWidget(self.card_table, 1); self.load_cards(); return page

        def load_cards(self) -> None:
            if not hasattr(self, "card_table"): return
            try: cards = asyncio.run(_card_display_rows(settings))
            except Exception: return
            self.card_table.setRowCount(len(cards))
            
            STATUS_MAP = {"AVAILABLE": "Có sẵn", "IN_USE": "Đang dùng", "LOST": "Đã mất", "LOCKED": "Bị khóa"}
            STATUS_COLOR = {"AVAILABLE": "#22c55e", "IN_USE": "#3b82f6", "LOST": "#f59e0b", "LOCKED": "#ef4444"}
            
            for r, (card, subscriber_name) in enumerate(cards):
                card_type_display = "Thuê bao" if card.card_type == "SUBSCRIBER" else "Vãng lai"
                status_text = STATUS_MAP.get(card.status, card.status)

                # Center-align cell items
                for c, value in enumerate((card.rfid_code, card_type_display, subscriber_name if card.card_type == "SUBSCRIBER" else "—")):
                    cell = QTableWidgetItem(str(value))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.card_table.setItem(r, c, cell)

                # Status badge widget (centered) — sized to fit its text so it never gets clipped
                status_w = QWidget(); sl = QHBoxLayout(status_w); sl.setContentsMargins(4, 6, 4, 6); sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_lbl = label(status_text, "badge", True)
                status_lbl.setStyleSheet(
                    f"background: {STATUS_COLOR.get(card.status, '#94a3b8')}; color: white; "
                    "padding: 4px 12px; border-radius: 10px; font-weight: bold; font-size: 12px;"
                )
                status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_lbl.adjustSize(); status_lbl.setMinimumWidth(status_lbl.sizeHint().width())
                sl.addWidget(status_lbl)
                self.card_table.setCellWidget(r, 3, status_w)
                self.card_table.setRowHeight(r, 44)
                self.card_table.resizeRowToContents(r)

                # Action buttons — same icon style as the Subscribers page
                actions = QWidget(); actions_row = QHBoxLayout(actions); actions_row.setContentsMargins(6, 4, 6, 4); actions_row.setSpacing(6)
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                edit.clicked.connect(lambda _=False, item=card: self.edit_card(item))
                remove.clicked.connect(lambda _=False, item=card: self.delete_card(item))
                actions_row.addWidget(edit); actions_row.addWidget(remove)
                self.card_table.setCellWidget(r, 4, actions)

        def add_card(self) -> None:
            self.card_dialog()

        def edit_card(self, card) -> None:
            self.card_dialog(card)

        def card_dialog(self, card=None) -> None:
            dialog, content, footer = modal_shell(self, "Thêm thẻ RFID" if not card else "Sửa thẻ RFID", 560)
            form = QFormLayout(); content.addLayout(form)
            
            uid = QLineEdit(card.rfid_code if card else ""); uid.setPlaceholderText("Quét hoặc nhập mã UID")
            if card: uid.setReadOnly(True)
            
            card_type = QComboBox(); card_type.addItem("Vãng lai", "GUEST"); card_type.addItem("Thuê bao", "SUBSCRIBER")
            
            subscriber = QComboBox(); subscriber.addItem("Chưa gán thuê bao", None)
            try:
                for item in asyncio.run(_subscriber_entities(settings)): subscriber.addItem(f"{item.full_name} — {item.phone}", item.id)
            except Exception: pass
            
            if card:
                card_type.setCurrentIndex(max(0, card_type.findData(card.card_type)))
                subscriber.setCurrentIndex(max(0, subscriber.findData(card.subscriber_id)))
            
            # Hide subscriber combo if card type is GUEST
            def type_changed():
                subscriber.setVisible(card_type.currentData() == "SUBSCRIBER")
            card_type.currentIndexChanged.connect(type_changed); type_changed()
            
            status = QComboBox()
            status.addItem("Có sẵn", "AVAILABLE"); status.addItem("Đang dùng", "IN_USE")
            status.addItem("Đã mất", "LOST"); status.addItem("Bị khóa", "LOCKED")
            if card: status.setCurrentIndex(max(0, status.findData(card.status)))
            
            form.addRow("Mã thẻ UID *", uid); form.addRow("Loại thẻ", card_type); form.addRow("Gán thuê bao", subscriber)
            if card: form.addRow("Trạng thái", status)
            
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thẻ" if not card else "Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            
            def save_card() -> None:
                try:
                    c_type, s_id = card_type.currentData(), subscriber.currentData()
                    if c_type == "GUEST": s_id = None
                    if card:
                        asyncio.run(_update_card(settings, card.id, c_type, s_id, status.currentData()))
                    else:
                        asyncio.run(_create_card(settings, uid.text(), c_type, s_id))
                    self.load_cards(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_card); dialog.exec()

        def delete_card(self, card) -> None:
            if QMessageBox.question(self, "Xóa thẻ", f"Xóa mềm thẻ {card.rfid_code}?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_card(settings, card.id)); self.load_cards()
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))

        def lane_page(self) -> QWidget:
            page, box = self.page(); box.setContentsMargins(16, 16, 16, 16)
            
            # Header
            header = QHBoxLayout()
            history_btn = QPushButton("↺ Lịch sử thay đổi"); history_btn.setStyleSheet("background: white; border: 1px solid #cbd5e1; color: #64748b; border-radius: 6px; padding: 6px 12px;")
            header.addWidget(history_btn)
            
            # Count label updated later
            self.lane_count_lbl = label("| 0 làn đang cấu hình", "muted")
            header.addWidget(self.lane_count_lbl)
            header.addStretch()
            
            add = QPushButton("+ Thêm làn xe"); add.setObjectName("primary")
            add.setStyleSheet("background: #f97316; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
            add.clicked.connect(self.add_lane)
            header.addWidget(add)
            box.addLayout(header)
            
            # Scroll Area for Grid
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet("background: transparent;")
            self.lane_container = QWidget()
            self.lane_grid = QGridLayout(self.lane_container)
            self.lane_grid.setSpacing(16)
            self.lane_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
            scroll.setWidget(self.lane_container)
            box.addWidget(scroll, 1)
            
            self.load_lanes()
            return page

        def load_lanes(self) -> None:
            if not hasattr(self, "lane_grid"): return
            
            # Clear grid
            while self.lane_grid.count():
                item = self.lane_grid.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            try: lanes = asyncio.run(_lanes(settings))
            except Exception: return
            
            self.lane_count_lbl.setText(f"| {len(lanes)} làn đang cấu hình")
            
            for index, lane in enumerate(lanes):
                card = QFrame(); card.setObjectName("card")
                card.setStyleSheet("QFrame#card { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
                cbox = QVBoxLayout(card); cbox.setContentsMargins(20, 20, 20, 20)
                
                # Header: Name + Car count
                header = QHBoxLayout()
                header.addWidget(label(lane.name, bold=True, style="font-size: 16px;"))
                header.addStretch()
                
                count_lbl = label("0", bold=True, style="color: #f59e0b; font-size: 18px;")
                txt_lbl = label("Xe đang gửi", "muted", style="font-size: 10px;")
                vbox = QVBoxLayout(); vbox.setSpacing(0); vbox.addWidget(count_lbl, 0, Qt.AlignmentFlag.AlignHCenter); vbox.addWidget(txt_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
                header.addLayout(vbox)
                cbox.addLayout(header)
                
                # Tags: Direction + Status
                tag_row = QHBoxLayout()
                if lane.direction == "IN": 
                    dir_lbl = label("↗ Xe vào", style="background: #dcfce7; color: #16a34a; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                elif lane.direction == "OUT":
                    dir_lbl = label("↙ Xe ra", style="background: #fee2e2; color: #dc2626; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                else:
                    dir_lbl = label("↔ Hai chiều", style="background: #e0e7ff; color: #4f46e5; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                
                status_lbl = label("● Hoạt động" if lane.is_active else "○ Tắt", style="background: #dcfce7; color: #16a34a; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                if not lane.is_active: status_lbl.setStyleSheet("background: #f1f5f9; color: #64748b; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                
                tag_row.addWidget(dir_lbl); tag_row.addWidget(status_lbl); tag_row.addStretch()
                cbox.addLayout(tag_row)
                
                cbox.addSpacing(15)
                cbox.addWidget(label("THIẾT BỊ LẮP ĐẶT", "muted", style="font-size: 11px; font-weight: bold;"))
                
                # Devices
                dev_row = QHBoxLayout()
                dev_style = "background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; border-radius: 6px; padding: 4px 8px; font-size: 11px;"
                if lane.rfid_device_id: dev_row.addWidget(label("💳 Đầu đọc thẻ", style=dev_style))
                if lane.camera_source: dev_row.addWidget(label("📷 Camera", style=dev_style))
                if lane.barrier_device_id: dev_row.addWidget(label("🚧 Barrier", style=dev_style))
                # Assuming finger print is not in our data model but we can show it grayed out if missing, or just not show
                dev_row.addStretch()
                cbox.addLayout(dev_row)
                
                cbox.addSpacing(15)
                cbox.addWidget(label("Trạng thái hoạt động: <b>Chờ xe</b>", style="color: #64748b; font-size: 12px;"))
                cbox.addSpacing(10)
                
                # Actions
                actions = QHBoxLayout()
                edit = QPushButton("📝 Sửa cấu hình")
                edit.setStyleSheet("background: white; border: 1px solid #93c5fd; color: #2563eb; border-radius: 6px; padding: 8px; font-weight: bold;")
                edit.clicked.connect(lambda _=False, item=lane: self.edit_lane(item))
                
                remove = QPushButton("🗑")
                remove.setStyleSheet("background: white; border: 1px solid #fca5a5; color: #dc2626; border-radius: 6px; padding: 8px 14px;")
                remove.clicked.connect(lambda _=False, item=lane: self.delete_lane(item))
                
                actions.addWidget(edit, 1)
                actions.addWidget(remove)
                cbox.addLayout(actions)
                
                self.lane_grid.addWidget(card, index // 2, index % 2)

        def show_lane_modal(self, lane=None):
            dialog = QDialog(self); dialog.setWindowTitle("Thêm làn xe mới" if not lane else "Sửa làn xe"); dialog.setFixedSize(500, 400)
            from PySide6.QtCore import Qt
            dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.FramelessWindowHint)
            dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            dialog.setStyleSheet("QDialog { background: transparent; } QLineEdit, QComboBox { padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; }")
            
            # Wrap everything in a main frame to handle rounded corners
            main_frame = QFrame(dialog)
            main_frame.setStyleSheet("QFrame { background: white; border-radius: 12px; }")
            box = QVBoxLayout(dialog); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(0)
            box.addWidget(main_frame)
            
            inner_box = QVBoxLayout(main_frame); inner_box.setContentsMargins(0, 0, 0, 0); inner_box.setSpacing(0)
            
            # Header
            header = QFrame(); header.setStyleSheet("background: #f97316; border-top-left-radius: 12px; border-top-right-radius: 12px;")
            hbox = QHBoxLayout(header); hbox.setContentsMargins(20, 15, 20, 15)
            title = label("+ Thêm làn xe mới" if not lane else "📝 Sửa làn xe", bold=True); title.setStyleSheet("color: white; font-size: 18px;")
            hbox.addWidget(title); hbox.addStretch()
            close_btn = QPushButton("✕"); close_btn.setStyleSheet("color: white; font-size: 18px; border: none; background: transparent;")
            close_btn.clicked.connect(dialog.reject); hbox.addWidget(close_btn)
            inner_box.addWidget(header)
            
            # Body
            body = QWidget(); vbox = QVBoxLayout(body); vbox.setContentsMargins(20, 20, 20, 20); vbox.setSpacing(15)
            
            # Name
            vbox.addWidget(label("Tên làn *", style="font-weight: bold; font-size: 12px; color: #475569;"))
            name = QLineEdit(lane.name if lane else ""); name.setPlaceholderText("VD: Làn vào 1, Làn ra A...")
            vbox.addWidget(name)
            vbox.addWidget(label("Tên hiển thị trên màn hình vận hành", "muted", style="font-size: 11px; margin-top: -10px;"))
            
            # Direction and Status in one row
            row = QHBoxLayout()
            col1 = QVBoxLayout(); col1.addWidget(label("Chiều xe", style="font-weight: bold; font-size: 12px; color: #475569;"))
            direction = QComboBox(); direction.addItems(["Xe vào (IN)", "Xe ra (OUT)", "Hai chiều (BOTH)"])
            
            # Map values to combo box indices
            dir_map = {"IN": 0, "OUT": 1, "BIDIRECTIONAL": 2}
            rev_dir_map = {0: "IN", 1: "OUT", 2: "BIDIRECTIONAL"}
            if lane: direction.setCurrentIndex(dir_map.get(lane.direction, 0))
            col1.addWidget(direction); row.addLayout(col1)
            
            col2 = QVBoxLayout(); col2.addWidget(label("Trạng thái", style="font-weight: bold; font-size: 12px; color: #475569;"))
            status = QComboBox(); status.addItems(["Hoạt động", "Tắt"])
            if lane and not lane.is_active: status.setCurrentIndex(1)
            col2.addWidget(status); row.addLayout(col2)
            
            vbox.addLayout(row)
            
            # Placeholder for devices (simplified for this modal based on screenshot)
            # The screenshot modal doesn't show the devices inputs, so we use defaults or keep existing if edit
            camera = lane.camera_source if lane else "cam1"
            rfid = lane.rfid_device_id if lane else "rfid1"
            barrier = lane.barrier_device_id if lane else "bar1"
            
            inner_box.addWidget(body); inner_box.addStretch()
            
            # Footer
            footer = QHBoxLayout(); footer.setContentsMargins(20, 10, 20, 20)
            footer.addStretch()
            cancel = QPushButton("Hủy"); cancel.setStyleSheet("background: #94a3b8; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
            save = QPushButton("💾 Lưu cấu hình"); save.setStyleSheet("background: #f97316; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
            cancel.clicked.connect(dialog.reject); footer.addWidget(cancel); footer.addWidget(save)
            inner_box.addLayout(footer)
            
            def do_save():
                try:
                    is_active = (status.currentIndex() == 0)
                    selected_dir = rev_dir_map[direction.currentIndex()]
                    if lane:
                        asyncio.run(_update_lane(settings, lane.id, name.text(), selected_dir, camera, rfid, barrier, is_active))
                    else:
                        asyncio.run(_create_lane(settings, name.text(), selected_dir, camera, rfid, barrier))
                    self.load_lanes(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Lỗi", str(exc))
            save.clicked.connect(do_save); dialog.exec()

        def add_lane(self) -> None:
            
            self.show_lane_modal()

        def edit_lane(self, lane) -> None:
            self.show_lane_modal(lane)

        def delete_lane(self, lane) -> None:
            if QMessageBox.question(self, "Xóa làn", f"Xóa mềm làn '{lane.name}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_lane(settings, lane.id)); self.load_lanes()
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))

        def load_subscribers(self) -> None:
            if not hasattr(self, "subscriber_table"): return
            try:
                data = asyncio.run(_subscriber_with_vehicles(settings))
                vehicle_names = asyncio.run(_vehicle_name_map(settings))
            except Exception: return
            self.subscriber_table.setRowCount(len(data))
            for r, (item, vehicles) in enumerate(data):
                vehicle_display = "\n".join([f"• {v.plate_number} ({vehicle_names.get(v.vehicle_type, v.vehicle_type)})" for v in vehicles]) if vehicles else "Không có xe"
                for c, value in enumerate((item.full_name, item.phone, getattr(item, "identity_card", ""), vehicle_display, item.valid_until.isoformat(), "Hoạt động" if item.is_active else "Đã khóa")):
                    cell_item = QTableWidgetItem(str(value))
                    cell_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.subscriber_table.setItem(r, c, cell_item)
                self.subscriber_table.resizeRowToContents(r)
                actions = QWidget()
                row = QHBoxLayout(actions); row.setContentsMargins(6, 4, 6, 4); row.setSpacing(6)
                edit = icon_btn("fa5s.user-edit", "Sửa", _BTN_EDIT_STYLE)
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                edit.clicked.connect(lambda _=False, subscriber=item, vlist=vehicles: self.subscriber_dialog(subscriber, vlist))
                remove.clicked.connect(lambda _=False, subscriber=item: self.delete_subscriber(subscriber))
                row.addWidget(edit); row.addWidget(remove)
                self.subscriber_table.setCellWidget(r, 6, actions)

        def add_subscriber(self) -> None:
            self.subscriber_dialog()

        def edit_subscriber(self, subscriber, vehicles) -> None:
            self.subscriber_dialog(subscriber, vehicles)

        def subscriber_dialog(self, subscriber=None, vehicles=None) -> None:
            dialog, content, footer = modal_shell(self, "Thêm thuê bao" if not subscriber else "Sửa thuê bao", 720)
            
            grid = QGridLayout(); content.addLayout(grid)
            
            name = QLineEdit(subscriber.full_name if subscriber else "")
            phone = QLineEdit(subscriber.phone if subscriber else "")
            email = QLineEdit(subscriber.email or "" if subscriber else "")
            identity_card = QLineEdit(getattr(subscriber, "identity_card", "") if subscriber else "")
            start = QLineEdit(subscriber.valid_from.isoformat() if subscriber else date.today().isoformat())
            end = QLineEdit(subscriber.valid_until.isoformat() if subscriber else date.today().replace(year=date.today().year + 1).isoformat())
            
            grid.addWidget(label("Họ và tên *", "muted"), 0, 0); grid.addWidget(name, 1, 0)
            grid.addWidget(label("Số điện thoại *", "muted"), 2, 0); grid.addWidget(phone, 3, 0)
            grid.addWidget(label("Email", "muted"), 4, 0); grid.addWidget(email, 5, 0)
            grid.addWidget(label("CMND/CCCD", "muted"), 6, 0); grid.addWidget(identity_card, 7, 0)
            grid.addWidget(label("Hiệu lực từ", "muted"), 8, 0); grid.addWidget(start, 9, 0)
            grid.addWidget(label("Hiệu lực đến", "muted"), 10, 0); grid.addWidget(end, 11, 0)
            
            if subscriber:
                active = QComboBox(); active.addItem("Hoạt động", True); active.addItem("Đã khóa", False)
                active.setCurrentIndex(0 if subscriber.is_active else 1)
                grid.addWidget(label("Trạng thái", "muted"), 12, 0); grid.addWidget(active, 13, 0)

            vehicle_group = QGroupBox("Phương tiện đăng ký"); grid.addWidget(vehicle_group, 0, 1, 14, 1)
            vehicle_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #d8e1ec; border-radius: 8px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #475569; }")
            v_layout = QVBoxLayout(vehicle_group)
            vehicle_list_layout = QVBoxLayout()
            v_layout.addLayout(vehicle_list_layout)
            v_layout.addStretch()
            
            add_v_btn = QPushButton("+ Thêm xe"); add_v_btn.setStyleSheet("background: #f1f5f9; color: #475569; border-radius: 4px; padding: 6px;")
            v_layout.addWidget(add_v_btn)
            
            vehicle_widgets = []
            
            def add_vehicle_row(plate="", v_type=""):
                row_w = QWidget(); r_lay = QHBoxLayout(row_w); r_lay.setContentsMargins(0,0,0,0)
                p_input = QLineEdit(plate); p_input.setPlaceholderText("Biển số")
                t_input = QComboBox(); self.fill_vehicle_combo(t_input)
                if v_type:
                    idx = t_input.findData(v_type)
                    if idx >= 0: t_input.setCurrentIndex(idx)
                del_btn = QPushButton("✕"); del_btn.setObjectName("danger"); del_btn.setFixedWidth(30)
                def remove_self():
                    vehicle_list_layout.removeWidget(row_w); row_w.deleteLater(); vehicle_widgets.remove((p_input, t_input))
                del_btn.clicked.connect(remove_self)
                r_lay.addWidget(p_input); r_lay.addWidget(t_input); r_lay.addWidget(del_btn)
                vehicle_list_layout.addWidget(row_w)
                vehicle_widgets.append((p_input, t_input))
                
            if vehicles:
                for v in vehicles:
                    add_vehicle_row(v.plate_number, v.vehicle_type)
            else:
                add_vehicle_row()
                
            add_v_btn.clicked.connect(lambda: add_vehicle_row())
            
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi" if subscriber else "Thêm thuê bao"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            
            def save_item() -> None:
                v_data = [{"plate_number": p.text().strip(), "vehicle_type": t.currentData()} for p, t in vehicle_widgets if p.text().strip()]
                try:
                    if subscriber:
                        asyncio.run(_update_subscriber(settings, subscriber.id, name.text(), phone.text(), email.text() or None, identity_card.text(), v_data, start.text(), end.text(), bool(active.currentData())))
                    else:
                        asyncio.run(_create_subscriber(settings, name.text(), phone.text(), email.text() or None, identity_card.text(), v_data, start.text(), end.text(), None))
                    self.load_subscribers(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_item); dialog.exec()

        def delete_subscriber(self, subscriber) -> None:
            if QMessageBox.question(self, "Xóa thuê bao", f"Xóa mềm thuê bao '{subscriber.full_name}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_subscriber(settings, subscriber.id)); self.load_subscribers()
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))

        def add_fee_rule(self) -> None:
            dialog, content, footer = modal_shell(self, "Thêm quy tắc phí", 620); form = QFormLayout(); content.addLayout(form)
            name, vehicle, block, price, free, surcharge, maximum = QLineEdit(), QComboBox(), QLineEdit("60"), QLineEdit("5000"), QLineEdit("0"), QLineEdit("0"), QLineEdit(); self.fill_vehicle_combo(vehicle)
            form.addRow("Tên quy tắc *", name); form.addRow("Loại xe", vehicle); form.addRow("Block tính (phút)", block); form.addRow("Giá mỗi block (VND)", price); form.addRow("Miễn phí (phút)", free); form.addRow("Phụ thu đêm (VND)", surcharge); form.addRow("Trần/ngày (VND, tùy chọn)", maximum)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu quy tắc"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_rule() -> None:
                try:
                    asyncio.run(_create_fee_rule(settings, name.text(), vehicle.currentData(), int(block.text()), int(price.text()), int(free.text()), int(surcharge.text()), int(maximum.text()) if maximum.text() else None)); dialog.accept(); self.reload_page("fees")
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_rule); dialog.exec()

        def edit_fee_rule(self, rule) -> None:
            dialog, content, footer = modal_shell(self, "Sửa quy tắc phí", 560); form = QFormLayout(); content.addLayout(form)
            name, vehicle, price, block, free, surcharge, maximum = QLineEdit(rule.name), QComboBox(), QLineEdit(str(rule.price_per_block)), QLineEdit(str(rule.block_minutes)), QLineEdit(str(rule.free_minutes)), QLineEdit(str(rule.night_surcharge or 0)), QLineEdit(str(rule.day_max or "")); self.fill_vehicle_combo(vehicle); vehicle.setCurrentIndex(max(0, vehicle.findData(rule.vehicle_type))); form.addRow("Tên", name); form.addRow("Loại xe", vehicle); form.addRow("Giá/block", price); form.addRow("Block (phút)", block); form.addRow("Miễn phí (phút)", free); form.addRow("Phụ thu đêm", surcharge); form.addRow("Trần/ngày", maximum)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_rule() -> None:
                try: asyncio.run(_update_fee_rule(settings, rule.id, name.text(), vehicle.currentData(), int(block.text()), int(price.text()), int(free.text()), int(surcharge.text()), int(maximum.text()) if maximum.text() else None)); dialog.accept(); self.reload_page("fees")
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_rule); dialog.exec()

        def delete_fee_rule(self, rule) -> None:
            if QMessageBox.question(self, "Xóa biểu phí", f"Xóa mềm quy tắc '{rule.name}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_fee_rule(settings, rule.id)); self.reload_page("fees")
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))

        def fill_vehicle_combo(self, combo: QComboBox) -> None:
            """Use configured vehicle types everywhere; display names stay user-friendly."""
            combo.clear()
            try:
                for item in asyncio.run(_vehicle_types(settings)):
                    combo.addItem(item.display_name, item.code)
            except Exception as exc:
                QMessageBox.warning(self, "Không tải được loại xe", str(exc))

        def vehicle_type_page(self) -> QWidget:
            page, box = self.page()
            row = QHBoxLayout(); title = label("Cấu hình loại xe", bold=True); title.setStyleSheet("font-size:24px;"); row.addWidget(title); row.addStretch()
            add = QPushButton("+ Thêm loại xe"); add.setObjectName("primary"); add.clicked.connect(self.add_vehicle_type); row.addWidget(add); box.addLayout(row)
            box.addWidget(label("Các biểu mẫu thuê bao, biểu phí và xe vào đều dùng danh mục này.", "muted"))
            self.vehicle_type_table = self.make_table(["Mã dùng trong hệ thống", "Tên hiển thị", "Thao tác"], 6); box.addWidget(self.vehicle_type_table, 1); self.load_vehicle_types()
            return page

        def load_vehicle_types(self) -> None:
            if not hasattr(self, "vehicle_type_table"): return
            try: rows = asyncio.run(_vehicle_types(settings))
            except Exception as exc: QMessageBox.warning(self, "Không tải được loại xe", str(exc)); return
            self.vehicle_type_table.setRowCount(len(rows))
            for r, item in enumerate(rows):
                self.vehicle_type_table.setItem(r, 0, QTableWidgetItem(item.code))
                self.vehicle_type_table.setItem(r, 1, QTableWidgetItem(item.display_name))
                actions = QWidget(); action_row = QHBoxLayout(actions); action_row.setContentsMargins(4, 2, 4, 2)
                edit = QPushButton("✎ Sửa"); remove = QPushButton("Xóa"); remove.setObjectName("danger")
                edit.clicked.connect(lambda _=False, row=item: self.edit_vehicle_type(row)); remove.clicked.connect(lambda _=False, row=item: self.delete_vehicle_type(row))
                action_row.addWidget(edit); action_row.addWidget(remove); self.vehicle_type_table.setCellWidget(r, 2, actions)

        def vehicle_type_dialog(self, item=None) -> None:
            dialog, content, footer = modal_shell(self, "Sửa loại xe" if item else "Thêm loại xe", 520)
            form = QFormLayout(); content.addLayout(form)
            code = QLineEdit(item.code if item else ""); name = QLineEdit(item.display_name if item else "")
            code.setPlaceholderText("Ví dụ: electric_bike"); name.setPlaceholderText("Ví dụ: Xe đạp điện")
            form.addRow("Mã loại xe *", code); form.addRow("Tên hiển thị *", name)
            hint = label("Mã chỉ dùng để liên kết dữ liệu; người dùng sẽ luôn thấy tên hiển thị.", "muted"); hint.setWordWrap(True); content.addWidget(hint)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu loại xe"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_item() -> None:
                try:
                    if item: asyncio.run(_update_vehicle_type(settings, item.id, code.text(), name.text()))
                    else: asyncio.run(_create_vehicle_type(settings, code.text(), name.text()))
                    dialog.accept(); self.reload_page("vehicle_types")
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_item); dialog.exec()

        def add_vehicle_type(self) -> None:
            self.vehicle_type_dialog()

        def edit_vehicle_type(self, item) -> None:
            self.vehicle_type_dialog(item)

        def delete_vehicle_type(self, item) -> None:
            if QMessageBox.question(self, "Xóa loại xe", f"Xóa mềm loại xe '{item.display_name}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_vehicle_type(settings, item.id)); self.reload_page("vehicle_types")
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))

        def accounts_page(self) -> QWidget:
            page, box = self.page(); header = QHBoxLayout(); h = label("Tài khoản & phân quyền", bold=True); h.setStyleSheet("font-size:24px;"); header.addWidget(h); header.addStretch(); roles = QPushButton("⚿ Vai trò & quyền"); roles.clicked.connect(self.manage_roles); header.addWidget(roles); create = QPushButton("+ Tạo tài khoản"); create.setObjectName("primary"); create.clicked.connect(self.create_account); header.addWidget(create); box.addLayout(header); self.user_table = self.make_table(["Tên đăng nhập", "Họ tên", "Vai trò", "Trạng thái", "Thao tác"]); box.addWidget(self.user_table, 1); self.load_users(); return page

        def load_users(self) -> None:
            if not hasattr(self, "user_table"): return
            try: users = asyncio.run(_users(settings))
            except Exception: return
            self.user_table.setRowCount(len(users))
            for r, user in enumerate(users):
                for c, value in enumerate((user.username, user.full_name, user.role, "Hoạt động" if user.is_active else "Đã khóa")): self.user_table.setItem(r, c, QTableWidgetItem(value))
                actions = QWidget(); action_row = QHBoxLayout(actions); action_row.setContentsMargins(4, 2, 4, 2)
                edit, remove = QPushButton("✎ Sửa"), QPushButton("Xóa"); remove.setObjectName("danger")
                edit.clicked.connect(lambda _=False, item=user: self.edit_account(item)); remove.clicked.connect(lambda _=False, item=user: self.delete_account(item))
                action_row.addWidget(edit); action_row.addWidget(remove); self.user_table.setCellWidget(r, 4, actions)

        def create_account(self) -> None:
            dialog, content, footer = modal_shell(self, "Tạo tài khoản", 520)
            form = QFormLayout(); content.addLayout(form); username, full_name, password, role = QLineEdit(), QLineEdit(), QLineEdit(), QComboBox(); password.setEchoMode(QLineEdit.EchoMode.Password)
            try: role.addItems([item.name for item in asyncio.run(_roles(settings))])
            except Exception: role.addItems(["OPERATOR"])
            form.addRow("Tên đăng nhập", username); form.addRow("Họ tên", full_name); form.addRow("Mật khẩu", password); form.addRow("Vai trò", role)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu tài khoản"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_account() -> None:
                if not username.text() or not full_name.text() or not password.text(): QMessageBox.warning(dialog, "Thiếu thông tin", "Nhập đủ tên đăng nhập, họ tên và mật khẩu."); return
                try: asyncio.run(_create_user(settings, username.text(), password.text(), full_name.text(), role.currentText())); self.load_users(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không tạo được", str(exc))
            save.clicked.connect(save_account); dialog.exec()

        def edit_account(self, user) -> None:
            dialog, content, footer = modal_shell(self, "Sửa tài khoản", 520); form = QFormLayout(); content.addLayout(form)
            full_name, password, role, active = QLineEdit(user.full_name), QLineEdit(), QComboBox(), QComboBox(); password.setPlaceholderText("Để trống nếu không đổi")
            password.setEchoMode(QLineEdit.EchoMode.Password)
            try: role.addItems([item.name for item in asyncio.run(_roles(settings))])
            except Exception: role.addItem(user.role)
            role.setCurrentText(user.role); active.addItem("Hoạt động", True); active.addItem("Đã khóa", False); active.setCurrentIndex(0 if user.is_active else 1)
            form.addRow("Tên đăng nhập", label(user.username, bold=True)); form.addRow("Họ tên", full_name); form.addRow("Mật khẩu mới", password); form.addRow("Vai trò", role); form.addRow("Trạng thái", active)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_item() -> None:
                try: asyncio.run(_update_user(settings, user.id, full_name.text(), role.currentText(), bool(active.currentData()), password.text() or None)); self.load_users(); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_item); dialog.exec()

        def delete_account(self, user) -> None:
            if user.id == getattr(self.user, "user_id"):
                QMessageBox.warning(self, "Không thể xóa", "Không thể xóa tài khoản đang đăng nhập."); return
            if QMessageBox.question(self, "Xóa tài khoản", f"Xóa mềm tài khoản '{user.username}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_user(settings, user.id)); self.load_users()
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))

        def manage_roles(self) -> None:
            dialog = QDialog(self); dialog.setWindowTitle("Vai trò và quyền"); dialog.setMinimumSize(600, 520); dialog.setStyleSheet(THEME); box = QVBoxLayout(dialog)
            box.addWidget(label("Tạo hoặc chỉnh sửa vai trò", bold=True)); selector = QComboBox(); selector.addItem("+ Vai trò mới"); name, description = QLineEdit(), QLineEdit(); name.setPlaceholderText("Tên vai trò, ví dụ: CASHIER"); description.setPlaceholderText("Mô tả vai trò")
            permissions = QListWidget(); permissions.setStyleSheet("background:#ffffff;color:#172033;border:1px solid #d8e1ec;border-radius:8px;")
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
            selector.currentIndexChanged.connect(select_role); box.addWidget(selector); box.addWidget(name); box.addWidget(description); permission_heading = QHBoxLayout(); permission_heading.addWidget(label("Các quyền được cấp", "muted")); permission_heading.addStretch(); add_permission = QPushButton("+ Thêm quyền"); permission_heading.addWidget(add_permission); box.addLayout(permission_heading); box.addWidget(permissions, 1)
            def add_permission_item() -> None:
                code, ok = QInputDialog.getText(dialog, "Thêm quyền", "Mã quyền (ví dụ: report.export):")
                if not ok or not code.strip(): return
                description_text, ok = QInputDialog.getText(dialog, "Thêm quyền", "Mô tả dễ hiểu:")
                if not ok: return
                try:
                    created_code, created_desc = asyncio.run(_create_permission(settings, code, description_text))
                    item = QListWidgetItem(f"{created_code} — {created_desc}"); item.setData(Qt.ItemDataRole.UserRole, created_code); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Checked); permissions.addItem(item)
                except Exception as exc: QMessageBox.warning(dialog, "Không tạo được quyền", str(exc))
            add_permission.clicked.connect(add_permission_item)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save); buttons.rejected.connect(dialog.reject)
            def save() -> None:
                if not name.text().strip(): QMessageBox.warning(dialog, "Thiếu tên", "Nhập tên vai trò."); return
                codes = {permissions.item(i).data(Qt.ItemDataRole.UserRole) for i in range(permissions.count()) if permissions.item(i).checkState() == Qt.CheckState.Checked}
                try: asyncio.run(_save_role(settings, name.text().strip().upper(), description.text().strip(), codes)); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            buttons.accepted.connect(save); box.addWidget(buttons); dialog.exec()

        def open_shift(self) -> None:
            dialog, content, footer = modal_shell(self, "Mở ca làm việc", 740)
            content.addWidget(label("Chọn ca làm việc", "muted"))
            preset_layout = QHBoxLayout()
            presets = [("Ca sáng", "06:00 - 14:00", "8 tiếng", "🌅"), ("Ca chiều", "14:00 - 22:00", "8 tiếng", "🌞"), ("Ca đêm", "22:00 - 06:00", "8 tiếng", "🌙"), ("Ca ngày đủ", "07:00 - 19:00", "12 tiếng", "📋")]
            self.selected_preset = presets[0]
            preset_buttons = []
            for name, time, dur, icon in presets:
                btn = QPushButton(); btn.setCheckable(True)
                btn.setStyleSheet("QPushButton { background: #ffffff; border: 1px solid #d8e1ec; border-radius: 10px; padding: 10px; } QPushButton:checked { border: 2px solid #ff7a1a; background: #fff0e4; }")
                vbox = QVBoxLayout(btn); icon_lbl = label(icon); icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); icon_lbl.setStyleSheet("font-size: 24px;")
                name_lbl = label(name, bold=True); name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); time_lbl = label(time, "muted"); time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dur_lbl = label(dur); dur_lbl.setStyleSheet("color:#ff7a1a; font-size:11px;"); dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                vbox.addWidget(icon_lbl); vbox.addWidget(name_lbl); vbox.addWidget(time_lbl); vbox.addWidget(dur_lbl)
                def on_click(checked, p=(name, time, dur, icon), button=btn):
                    if checked:
                        for b in preset_buttons:
                            if b != button: b.setChecked(False)
                        self.selected_preset = p; update_summary()
                btn.clicked.connect(on_click); preset_buttons.append(btn); preset_layout.addWidget(btn)
            preset_buttons[0].setChecked(True); content.addLayout(preset_layout); content.addSpacing(15)
            grid = QGridLayout()
            grid.addWidget(label("Làn phụ trách", "muted"), 0, 0); lane_cb = QComboBox(); lane_cb.addItem("-- Tất cả làn --")
            try:
                for ln in asyncio.run(_lanes(settings)): lane_cb.addItem(ln.name)
            except Exception: pass
            grid.addWidget(lane_cb, 1, 0); grid.addWidget(label("Loại ca", "muted"), 0, 1); type_cb = QComboBox()
            for name, time, _, _ in presets: type_cb.addItem(f"{name} ({time})")
            grid.addWidget(type_cb, 1, 1); grid.addWidget(label("Tiền đầu ca (VNĐ)", "muted"), 2, 0); cash_cb = QComboBox(); cash_cb.addItems(["Không có tiền đầu ca", "500.000 đ", "1.000.000 đ", "2.000.000 đ", "5.000.000 đ", "Số tiền khác..."])
            grid.addWidget(cash_cb, 3, 0); grid.addWidget(label("Ghi chú bổ sung", "muted"), 2, 1); note_cb = QComboBox(); note_cb.addItems(["-- Không có ghi chú --", "Bàn giao với ca trước", "Bàn giao cho ca sau", "Thiết bị cần kiểm tra", "Có sự cố cần báo cáo", "Ngày lễ - lưu lượng cao", "Ca cuối tuần"])
            grid.addWidget(note_cb, 3, 1); content.addLayout(grid); content.addSpacing(15)
            summary_frame = QFrame(); summary_frame.setStyleSheet("background: #f4f8fb; border-radius: 8px; border: 1px dashed #c0d1e1;")
            sum_vbox = QVBoxLayout(summary_frame); title_lbl = label("ℹ Thông tin ca sẽ mở", bold=True); title_lbl.setStyleSheet("color: #2b6cb0; margin-bottom: 5px;")
            sum_vbox.addWidget(title_lbl); sum_type = label("Loại ca: Ca sáng"); sum_lane = label("Làn: -- Tất cả làn --"); sum_note = label("Ghi chú: Ca sáng (06:00-14:00)")
            sum_vbox.addWidget(sum_type); sum_vbox.addWidget(sum_lane); sum_vbox.addWidget(sum_note); content.addWidget(summary_frame)
            def update_summary():
                sum_type.setText(f"Loại ca: <b>{self.selected_preset[0]}</b>")
                sum_lane.setText(f"Làn: <b>{lane_cb.currentText()}</b>")
                sum_note.setText(f"Ghi chú: <b>{self.selected_preset[0]} ({self.selected_preset[1]})</b>")
                type_cb.setCurrentText(f"{self.selected_preset[0]} ({self.selected_preset[1]})")
            lane_cb.currentTextChanged.connect(update_summary)
            def type_changed(txt):
                for b, p in zip(preset_buttons, presets):
                    if p[0] in txt:
                        b.setChecked(True)
                        self.selected_preset = p
                        update_summary()
            type_cb.currentTextChanged.connect(type_changed); update_summary()
            cancel, save = QPushButton("Hủy"), QPushButton("▶ Mở ca ngay"); save.setObjectName("success"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def do_open():
                # Extract cash input
                cash_text = cash_cb.currentText()
                start_cash = 0
                if "500.000" in cash_text: start_cash = 500000
                elif "1.000.000" in cash_text: start_cash = 1000000
                elif "2.000.000" in cash_text: start_cash = 2000000
                elif "5.000.000" in cash_text: start_cash = 5000000
                
                # Extract lane
                lane_txt = lane_cb.currentText()
                lane_id = next((l.id for l in lanes if l.name == lane_txt), None)
                
                # Extract notes
                note_txt = note_cb.currentText() if "Không có" not in note_cb.currentText() else ""
                
                try:
                    self.shift_id = asyncio.run(_open_shift(settings, getattr(self.user, "user_id"), lane_id, self.selected_preset[0], start_cash, note_txt))
                except Exception as exc: QMessageBox.warning(dialog, "Không thể mở ca", str(exc)); return
                self.shift_status_badge.setText("Ca đang hoạt động"); self.shift_status_badge.setStyleSheet("background: #dcfce7; color: #166534; border: 1px solid #bbf7d0;")
                self.shift_button.setText("✓ Ca đang hoạt động")
                self.refresh_live(); dialog.accept()
            save.clicked.connect(do_open); dialog.exec()

        def record_entry(self, lane_id: str) -> None:
            if not self.shift_id: QMessageBox.warning(self, "Chưa mở ca", "Hãy mở ca làm việc trước."); return
            plate, ok = QInputDialog.getText(self, "Xe vào", "Biển số xe:");
            if not ok or not plate.strip(): return
            try:
                vehicle_types = asyncio.run(_vehicle_types(settings))
            except Exception as exc:
                QMessageBox.warning(self, "Không tải được loại xe", str(exc)); return
            labels = [item.display_name for item in vehicle_types]
            vehicle, ok = QInputDialog.getItem(self, "Loại xe", "Chọn loại xe:", labels, 0, False)
            if not ok: return
            vehicle_code = next((item.code for item in vehicle_types if item.display_name == vehicle), None)
            try: asyncio.run(_entry(settings, lane_id, plate.strip(), vehicle_code, self.shift_id)); self.refresh_live()
            except Exception as exc: QMessageBox.warning(self, "Không thể ghi xe vào", str(exc))

        def record_exit(self, lane_id: str) -> None:
            plate, ok = QInputDialog.getText(self, "Xe ra", "Biển số xe:");
            if not ok or not plate.strip(): return
            try: fee, minutes = asyncio.run(_exit(settings, lane_id, plate.strip())); QMessageBox.information(self, "Xe ra", f"Phí: {fee:,} VND\nThời gian: {minutes} phút"); self.refresh_live()
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

async def _open_shift(settings: Settings, user_id: str, lane_id: str | None = None, note: str = "", opening_cash: int = 0) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: 
            inp = OpenShiftInput(settings.branch_id, user_id, lane_id, note, opening_cash)
            return (await OpenShiftUseCase(SQLiteShiftRepository(session)).execute(inp)).shift_id
    finally: await db.dispose()

async def _close_shift(settings: Settings, user_id: str, actual_ending_cash: int | None, closing_notes: str | None):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await CloseShiftUseCase(SQLiteShiftRepository(session), SQLiteSessionRepository(session)).execute(CloseShiftInput(user_id, actual_ending_cash, closing_notes))
    finally: await db.dispose()

async def _entry(settings: Settings, lane_id: str, plate: str, vehicle: str, shift_id: str) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            output = await VehicleEntryUseCase(SQLiteSessionRepository(session), SQLiteVehicleRepository(session), SQLiteCardRepository(session), SQLiteFeeRuleRepository(session), SQLiteSubscriberRepository(session), SQLiteLaneRepository(session), MockBarrierController(), SQLiteSyncOutboxWriter(session)).execute(VehicleEntryInput(lane_id, plate_number=plate, vehicle_type=vehicle, shift_id=shift_id)); return output.session_id
    finally: await db.dispose()

async def _exit(settings: Settings, lane_id: str, plate: str) -> tuple[int, int]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            output = await VehicleExitUseCase(SQLiteSessionRepository(session), SQLiteCardRepository(session), SQLiteFeeRuleRepository(session), SQLiteSubscriberRepository(session), SQLiteVehicleRepository(session), MockBarrierController(), FeeCalculator(), SQLiteSyncOutboxWriter(session)).execute(VehicleExitInput(lane_id, plate_number=plate)); return output.fee_amount, output.duration_minutes
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

async def _update_user(settings: Settings, user_id: str, full_name: str, role: str, is_active: bool, password: str | None) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await UserManagementUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher()).update(UserUpdateInput(user_id, full_name, role, is_active, password))
    finally: await db.dispose()

async def _delete_user(settings: Settings, user_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await UserManagementUseCase(SQLiteUserRepository(session), PBKDF2PasswordHasher()).delete(user_id)
    finally: await db.dispose()

async def _create_subscriber(settings: Settings, full_name: str, phone: str, email: str | None, identity_card: str, vehicles: list[dict[str, str]], valid_from: str, valid_until: str, rfid_code: str | None) -> None:
    if not full_name.strip() or not phone.strip(): raise ValueError("Họ tên và số điện thoại là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await RegisterSubscriberUseCase(SQLiteSubscriberRepository(session), SQLiteCardRepository(session), SQLiteVehicleRepository(session)).execute(RegisterSubscriberInput(settings.branch_id, full_name.strip(), phone.strip(), identity_card.strip(), vehicles, date.fromisoformat(valid_from), date.fromisoformat(valid_until), email, rfid_code))
    finally: await db.dispose()

async def _create_fee_rule(settings: Settings, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None, is_active: bool = True) -> None:
    if not name.strip(): raise ValueError("Tên quy tắc là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteFeeRuleRepository(session)
            rule = FeeRuleInput(settings.branch_id, name.strip(), vehicle_type, free_minutes, block_minutes, price_per_block, day_max)
            rule_id = await FeeRuleManagementUseCase(repo).create(rule)
            created = await repo.get_by_id(rule_id)
            if created is not None:
                created.night_surcharge = night_surcharge or None
                await repo.update(created)
    finally: await db.dispose()

async def _update_fee_rule(settings: Settings, rule_id: str, name: str, vehicle_type: str, block_minutes: int, price_per_block: int, free_minutes: int, night_surcharge: int, day_max: int | None, is_active: bool = True) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteFeeRuleRepository(session)
            await FeeRuleManagementUseCase(repo).update(rule_id, FeeRuleInput(settings.branch_id, name, vehicle_type, free_minutes, block_minutes, price_per_block, day_max, is_active))
            rule = await repo.get_by_id(rule_id)
            if rule is not None:
                rule.night_surcharge = night_surcharge or None
                await repo.update(rule)
    finally: await db.dispose()

async def _delete_fee_rule(settings: Settings, rule_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await FeeRuleManagementUseCase(SQLiteFeeRuleRepository(session)).delete(rule_id)
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

async def _subscriber_entities(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteSubscriberRepository(session).list_all()
    finally: await db.dispose()

async def _subscriber_with_vehicles(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            subscribers = await SQLiteSubscriberRepository(session).list_all()
            vehicles = []
            for sub in subscribers:
                sub_vehicles = await SQLiteVehicleRepository(session).list_by_subscriber(sub.id)
                vehicles.append(sub_vehicles)
            return list(zip(subscribers, vehicles))
    finally: await db.dispose()

async def _update_subscriber(settings: Settings, subscriber_id: str, full_name: str, phone: str, email: str | None, identity_card: str, vehicles: list[dict[str, str]], valid_from: str, valid_until: str, is_active: bool) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await SubscriberManagementUseCase(SQLiteSubscriberRepository(session), SQLiteVehicleRepository(session)).update(SubscriberUpdateInput(subscriber_id, full_name, phone, identity_card, vehicles, date.fromisoformat(valid_from), date.fromisoformat(valid_until), email, is_active))
    finally: await db.dispose()

async def _delete_subscriber(settings: Settings, subscriber_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await SubscriberManagementUseCase(SQLiteSubscriberRepository(session), SQLiteVehicleRepository(session)).delete(subscriber_id)
    finally: await db.dispose()

async def _card_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: rows = await SQLiteCardRepository(session).list_all()
        return [(c.rfid_code, c.subscriber_id or "—", c.vehicle_id or "—", "Hoạt động" if c.is_active else "Đã khóa") for c in rows]
    finally: await db.dispose()

async def _card_entities(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteCardRepository(session).list_all()
    finally: await db.dispose()

async def _card_display_rows(settings: Settings):
    """Resolve internal foreign keys to end-user labels before rendering UI."""
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            cards = await SQLiteCardRepository(session).list_all()
            subscribers = {item.id: item for item in await SQLiteSubscriberRepository(session).list_all()}
        rows = []
        for card in cards:
            subscriber = subscribers.get(card.subscriber_id or "")
            display = f"{subscriber.full_name} · {subscriber.phone}" if subscriber else "Chưa gán thuê bao"
            rows.append((card, display))
        return rows
    finally: await db.dispose()

async def _create_card(settings: Settings, rfid_code: str, card_type: str, subscriber_id: str | None) -> None:
    if not rfid_code.strip(): raise ValueError("Mã UID là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteCardRepository(session)
            if await repo.get_by_rfid_code(rfid_code.strip()): raise ValueError("Mã UID đã tồn tại")
            await repo.create(Card(branch_id=settings.branch_id, rfid_code=rfid_code.strip(), card_type=card_type, subscriber_id=subscriber_id, status="AVAILABLE"))
    finally: await db.dispose()

async def _update_card(settings: Settings, card_id: str, card_type: str, subscriber_id: str | None, status: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteCardRepository(session); card = await repo.get_by_id(card_id)
            if card is None: raise ValueError("Không tìm thấy thẻ")
            card.card_type, card.subscriber_id, card.status = card_type, subscriber_id, status
            await repo.update(card)
    finally: await db.dispose()

async def _delete_card(settings: Settings, card_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await SQLiteCardRepository(session).delete(card_id)
    finally: await db.dispose()

async def _lanes(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteLaneRepository(session).list_active()
    finally: await db.dispose()

async def _create_lane(settings: Settings, name: str, direction: str, camera: str | None, rfid: str | None, barrier: str | None) -> None:
    if not name.strip(): raise ValueError("Tên làn là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await SQLiteLaneRepository(session).create(Lane(branch_id=settings.branch_id, name=name.strip(), direction=direction, camera_source=camera, rfid_device_id=rfid, barrier_device_id=barrier))
    finally: await db.dispose()

async def _update_lane(settings: Settings, lane_id: str, name: str, direction: str, camera: str | None, rfid: str | None, barrier: str | None, is_active: bool) -> None:
    if not name.strip(): raise ValueError("Tên làn là bắt buộc")
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteLaneRepository(session); lane = await repo.get_by_id(lane_id)
            if lane is None: raise ValueError("Không tìm thấy làn")
            lane.name, lane.direction = name.strip(), direction
            lane.camera_source, lane.rfid_device_id, lane.barrier_device_id, lane.is_active = camera, rfid, barrier, is_active
            await repo.update(lane)
    finally: await db.dispose()

async def _delete_lane(settings: Settings, lane_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            active_sessions = await SQLiteSessionRepository(session).list_recent(settings.branch_id, 10000)
            if any(item.status == "ACTIVE" and item.lane_in_id == lane_id for item in active_sessions):
                raise ValueError("Không thể xóa làn đang có xe trong bãi")
            await SQLiteLaneRepository(session).delete(lane_id)
    finally: await db.dispose()

async def _shift_rows(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            rows = await SQLiteShiftRepository(session).list_by_branch(settings.branch_id, 100)
            users = {item.id: item.full_name for item in await SQLiteUserRepository(session).list_all()}
        return [(users.get(s.operator_id, "Nhân viên không còn hoạt động"), s.start_time.strftime("%d/%m %H:%M"), s.end_time.strftime("%d/%m %H:%M") if s.end_time else "—", f"{s.total_revenue:,} đ", s.status) for s in rows]
    finally: await db.dispose()

async def _shift_entities(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteShiftRepository(session).list_by_branch(settings.branch_id, 100)
    finally: await db.dispose()

async def _create_shift(settings: Settings, inp: ShiftInput) -> str:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await ShiftManagementUseCase(SQLiteShiftRepository(session)).create(inp)
    finally: await db.dispose()

async def _update_shift(settings: Settings, shift_id: str, inp: ShiftInput) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await ShiftManagementUseCase(SQLiteShiftRepository(session)).update(shift_id, inp)
    finally: await db.dispose()

async def _delete_shift(settings: Settings, shift_id: str) -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: await ShiftManagementUseCase(SQLiteShiftRepository(session)).delete(shift_id)
    finally: await db.dispose()

async def _close_shift(settings: Settings, operator_id: str, closing_cash: int = 0, close_note: str = "") -> None:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            await CloseShiftUseCase(SQLiteShiftRepository(session), SQLiteSessionRepository(session)).execute(CloseShiftInput(operator_id, closing_cash, close_note))
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

async def _vehicle_types(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteVehicleTypeRepository(session).list_all()
    finally: await db.dispose()

async def _vehicle_name_map(settings: Settings) -> dict[str, str]:
    return {item.code: item.display_name for item in await _vehicle_types(settings)}

async def _create_vehicle_type(settings: Settings, code: str, display_name: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteVehicleTypeRepository(session).create(code, display_name)
    finally: await db.dispose()

async def _update_vehicle_type(settings: Settings, item_id: str, code: str, display_name: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteVehicleTypeRepository(session).update(item_id, code, display_name)
    finally: await db.dispose()

async def _delete_vehicle_type(settings: Settings, item_id: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            types = await SQLiteVehicleTypeRepository(session).list_all()
            current = next((item for item in types if item.id == item_id), None)
            if current is None: raise ValueError("Không tìm thấy loại xe")
            subscribers = await SQLiteSubscriberRepository(session).list_all()
            fee_rules = await SQLiteFeeRuleRepository(session).list_all()
            if any(item.vehicle_type == current.code for item in subscribers) or any(item.vehicle_type == current.code for item in fee_rules):
                raise ValueError("Không thể xóa loại xe đang được dùng trong thuê bao hoặc biểu phí")
            await SQLiteVehicleTypeRepository(session).delete(item_id)
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

async def _create_permission(settings: Settings, code: str, description: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await SQLiteAuthorizationRepository(session).create_permission(code, description)
    finally: await db.dispose()

async def _role_permissions(settings: Settings, role_name: str) -> set[str]:
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            repo = SQLiteAuthorizationRepository(session)
            await repo.ensure_starter_roles()
            for role in await repo.list_roles():
                if role.name == role_name:
                    return set(role.permission_codes)
            return set()
    finally: await db.dispose()

async def _save_role(settings: Settings, name: str, description: str, codes: set[str]):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session: return await SQLiteAuthorizationRepository(session).save_role(name, description, codes)
    finally: await db.dispose()