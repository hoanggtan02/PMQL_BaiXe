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
from pmql.infrastructure.hardware.rfid_tcp import run_rfid_server_in_thread
from PySide6.QtCore import QObject, Signal

class HardwareSignals(QObject):
    rfid_scanned = Signal(str, str)  # ip_address, rfid_code

global_hw_signals = HardwareSignals()

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

    # Initialize missing database tables automatically on startup
    async def _init_db():
        db = Database(settings.local_database_url)
        await db.create_all()
        await db.dispose()
    asyncio.run(_init_db())

    # Start background TCP Server for RFID
    def on_rfid_read(ip, rfid_code):
        global_hw_signals.rfid_scanned.emit(ip, rfid_code)
    
    # Run on default port 9001 (can be taken from settings in the future)
    run_rfid_server_in_thread(9001, on_rfid_read)


    # --- Icon button helper ---
    _BTN_ICON_STYLE = (
        "QPushButton { border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; }"
    )
    _BTN_EDIT_STYLE = "QPushButton { background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; } QPushButton:hover { background: #2563eb; }"
    _BTN_DEL_STYLE  = "QPushButton { background: #ef4444; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; } QPushButton:hover { background: #dc2626; }"
    _BTN_PLAIN_STYLE = "QPushButton { background: #64748b; color: white; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; } QPushButton:hover { background: #475569; }"

    def icon_btn(icon_name: str, text: str, style: str = _BTN_EDIT_STYLE, size: int = 16, icon_color: str = "white") -> QPushButton:
        btn = QPushButton()
        symbol_map = {
            "fa5s.edit": "✎",
            "fa5s.trash-alt": "🗑",
            "fa5s.user-edit": "👤",
            "fa5s.plus": "➕"
        }
        sym = symbol_map.get(icon_name, "")
        btn.setText(f"{sym} {text}" if sym else text)
        btn.setStyleSheet(style)
        btn.setFixedHeight(30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
            super().__init__()
            self.setWindowTitle("PMQL Bãi Xe"); self.setMinimumSize(980, 620); self.setStyleSheet(THEME)
            root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

            # Left brand panel
            brand = QFrame(); brand.setObjectName("sidebar")
            left = QVBoxLayout(brand); left.setContentsMargins(56, 0, 56, 0)
            left.addStretch(2)

            # Logo badge
            logo_row = QHBoxLayout()
            mark = QLabel("P"); mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mark.setFixedSize(52, 52)
            mark.setStyleSheet("background: #f97316; border-radius: 14px; font-size: 26px; font-weight: 800; color: white;")
            logo_row.addWidget(mark); logo_row.addStretch()
            left.addLayout(logo_row)
            left.addSpacing(24)

            brand_title = label("PMQL Bãi Xe", bold=True)
            brand_title.setObjectName("sidebarBrand")
            brand_title.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800;")
            left.addWidget(brand_title)
            brand_sub = label("Hệ thống quản lý bãi xe thông minh")
            brand_sub.setStyleSheet("color: #64748b; font-size: 13px; margin-top: 4px;")
            left.addWidget(brand_sub)
            left.addSpacing(40)

            # Feature list
            features = [
                ("→", "Vận hành làn xe thời gian thực"),
                ("→", "Quản lý thuê bao & thẻ RFID"),
                ("→", "Báo cáo doanh thu và ca làm việc"),
                ("→", "Phân quyền tài khoản vận hành"),
            ]
            for arrow, feat_text in features:
                feat_row = QHBoxLayout(); feat_row.setSpacing(10)
                arr = label(arrow); arr.setStyleSheet("color: #f97316; font-size: 14px; font-weight: 700;")
                arr.setFixedWidth(16)
                txt = label(feat_text); txt.setStyleSheet("color: #94a3b8; font-size: 13px;")
                feat_row.addWidget(arr); feat_row.addWidget(txt); feat_row.addStretch()
                left.addLayout(feat_row); left.addSpacing(10)
            left.addStretch(3)

            # Right form panel
            form_box = QFrame()
            form_box.setStyleSheet("QFrame { background: #ffffff; border: none; }")
            form = QVBoxLayout(form_box); form.setContentsMargins(64, 0, 64, 0)
            form.addStretch(2)
            h = label("Đăng nhập", bold=True); h.setStyleSheet("font-size: 28px; font-weight: 800; color: #0f172a;")
            form.addWidget(h)
            sub = label("Chào mừng bạn quay lại hệ thống."); sub.setStyleSheet("color: #64748b; font-size: 13px; margin-top: 4px; margin-bottom: 28px;")
            form.addWidget(sub)

            user_label = label("Tên đăng nhập"); user_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;")
            form.addWidget(user_label)
            self.username = QLineEdit("admin"); self.username.setPlaceholderText("admin")
            self.username.setStyleSheet("QLineEdit { padding: 12px 16px; font-size: 14px; }")
            form.addWidget(self.username); form.addSpacing(16)

            pass_label = label("Mật khẩu"); pass_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;")
            form.addWidget(pass_label)
            self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password); self.password.setPlaceholderText("••••••••")
            self.password.setStyleSheet("QLineEdit { padding: 12px 16px; font-size: 14px; }")
            form.addWidget(self.password); form.addSpacing(24)

            submit = QPushButton("Đăng nhập")
            submit.setObjectName("primary")
            submit.setCursor(Qt.CursorShape.PointingHandCursor)
            submit.setObjectName("primary")
            submit.setFixedHeight(48)
            submit.setStyleSheet("QPushButton { font-size: 15px; font-weight: 700; }")
            submit.clicked.connect(self.sign_in); self.password.returnPressed.connect(self.sign_in)
            form.addWidget(submit)

            self.notice = label("", "muted"); self.notice.setStyleSheet("color: #ef4444; font-size: 12px; margin-top: 8px;")
            form.addWidget(self.notice)
            form.addStretch(3)
            hint = label("Tài khoản mặc định: admin / 123")
            hint.setStyleSheet("color: #94a3b8; font-size: 11px; text-align: center;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            form.addWidget(hint); form.addSpacing(20)

            root.addWidget(brand, 5); root.addWidget(form_box, 4)

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
            self.page_factories = {"overview": self.overview_page, "operations": self.operations_page, "sessions": self.session_page, "shifts": self.shift_page, "subscribers": self.subscriber_page, "cards": self.card_page, "alerts": lambda: self.table_page("Cảnh báo", ["Loại", "Mức độ", "Nội dung", "Thời gian", "Trạng thái"], _alert_rows), "fees": self.fee_page, "lanes": self.lane_page, "vehicle_types": self.vehicle_type_page, "accounts": self.accounts_page, "settings": self.settings_page, "hardware": self.hardware_page}
            self.pages = {key: factory() for key, factory in self.page_factories.items()}
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: [self._apply_interaction_cursors(page) for page in self.pages.values()])

            for page in self.pages.values():
                self.stack.addWidget(page)
            self.go("overview")

        def build_sidebar(self) -> QWidget:
            from PySide6.QtCore import QTimer
            side = QFrame(); side.setObjectName("sidebar")
            side.setMinimumWidth(240); side.setMaximumWidth(256)
            box = QVBoxLayout(side); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(0)

            # Logo area
            logo_area = QWidget()
            logo_area.setStyleSheet("background: transparent;")
            logo_layout = QHBoxLayout(logo_area); logo_layout.setContentsMargins(20, 20, 20, 16)
            mark = QLabel("P"); mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mark.setFixedSize(36, 36)
            mark.setStyleSheet("background: #f97316; border-radius: 10px; font-size: 18px; font-weight: 800; color: white;")
            logo_layout.addWidget(mark)
            title_col = QVBoxLayout(); title_col.setSpacing(1); title_col.setContentsMargins(0,0,0,0)
            brand_lbl = label("PMQL BÃI XE", bold=True); brand_lbl.setObjectName("sidebarBrand")
            brand_lbl.setStyleSheet("color: #f1f5f9; font-size: 13px; font-weight: 700; padding: 0;")
            sub_lbl2 = label("Quản lý bãi xe"); sub_lbl2.setObjectName("sidebarSub")
            sub_lbl2.setStyleSheet("color: #475569; font-size: 10px; padding: 0;")
            title_col.addWidget(brand_lbl); title_col.addWidget(sub_lbl2)
            logo_layout.addLayout(title_col, 1)
            box.addWidget(logo_area)

            # Divider
            div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
            div.setStyleSheet("border: none; border-top: 1px solid #1e293b;")
            box.addWidget(div); box.addSpacing(8)

            # Nav scroll area
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { width: 4px; }")
            nav_widget = QWidget(); nav_widget.setStyleSheet("background: transparent;")
            nav_box = QVBoxLayout(nav_widget); nav_box.setContentsMargins(0, 0, 0, 0); nav_box.setSpacing(0)

            groups = [
                ("", [
                    ("overview",    "▦  Tổng quan"),
                    ("operations",  "➡  Vận hành làn"),
                    ("sessions",    "◌  Phiên gửi xe"),
                    ("alerts",      "⚠  Cảnh báo"),
                    ("shifts",      "◴  Ca làm việc"),
                ]),
                ("QUẢN LÝ", [
                    ("subscribers", "▣  Thuê bao"),
                    ("cards",       "▤  Thẻ xe"),
                    ("fees",        "◆  Biểu phí"),
                    ("lanes",       "⚙  Cấu hình làn"),
                    ("vehicle_types","▧  Loại xe"),
                ]),
                ("HỆ THỐNG", [
                    ("accounts",    "♙  Tài khoản"),
                    ("settings",    "⚙  Cài đặt"),
                    ("hardware",    "⚡  Kết nối TB"),
                ]),
            ]
            required = {"operations": "lane.operate", "sessions": "session.view", "alerts": "alert.manage", "shifts": "shift.manage", "subscribers": "subscriber.manage", "cards": "card.manage", "fees": "fee.manage", "lanes": "lane.view", "vehicle_types": "fee.manage", "accounts": "user.manage"}
            for group, links in groups:
                if group:
                    g_lbl = label(group, "section")
                    g_lbl.setStyleSheet("color: #475569; font-size: 10px; font-weight: 700; padding: 16px 20px 6px; letter-spacing: 1.5px;")
                    nav_box.addWidget(g_lbl)
                for key, text in links:
                    if key in required and required[key] not in self.permission_codes: continue
                    button = QPushButton(text); button.setObjectName("nav")
                    button.setCursor(Qt.CursorShape.PointingHandCursor)
                    button.clicked.connect(lambda _=False, target=key: self.go(target))
                    nav_box.addWidget(button); self.nav[key] = button
            nav_box.addStretch()
            scroll.setWidget(nav_widget); box.addWidget(scroll, 1)

            # User footer
            footer_div = QFrame(); footer_div.setFrameShape(QFrame.Shape.HLine)
            footer_div.setStyleSheet("border: none; border-top: 1px solid #1e293b;")
            box.addWidget(footer_div)
            footer_area = QWidget(); footer_area.setStyleSheet("background: transparent;")
            footer_lay = QVBoxLayout(footer_area); footer_lay.setContentsMargins(20, 12, 20, 16); footer_lay.setSpacing(2)
            user_section = label("ĐANG ĐĂNG NHẬP")
            user_section.setStyleSheet("color: #334155; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;")
            footer_lay.addWidget(user_section)
            uname = label(getattr(self.user, "full_name"), bold=True)
            uname.setStyleSheet("color: #f1f5f9; font-size: 13px; font-weight: 700;")
            footer_lay.addWidget(uname)
            role_txt = getattr(self.user, "role", "")
            role_colors = {"admin": ("#fff7ed", "#c2410c", "#fed7aa"), "operator": ("#f0fdf4", "#15803d", "#bbf7d0")}
            rbg, rcolor, rborder = role_colors.get(role_txt, ("#f1f5f9", "#475569", "#e2e8f0"))
            role_badge = label(role_txt)
            role_badge.setStyleSheet(f"background: {rbg}; color: {rcolor}; border: 1px solid {rborder}; border-radius: 8px; padding: 2px 8px; font-size: 10px; font-weight: 700;")
            footer_lay.addWidget(role_badge)
            box.addWidget(footer_area)
            return side

        def build_header(self) -> QWidget:
            from PySide6.QtCore import QTimer
            bar = QFrame(); bar.setObjectName("header"); bar.setFixedHeight(56)
            row = QHBoxLayout(bar); row.setContentsMargins(28, 0, 24, 0); row.setSpacing(12)

            self.breadcrumb = label("", bold=True)
            self.breadcrumb.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
            row.addWidget(self.breadcrumb); row.addStretch()

            # Clock
            self.header_clock = label("")
            self.header_clock.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600; font-family: 'Consolas', monospace;")
            def _tick(): self.header_clock.setText(datetime.now().strftime("%H:%M:%S  %d/%m/%Y"))
            _tick()
            timer = QTimer(bar); timer.timeout.connect(_tick); timer.start(1000)
            row.addWidget(self.header_clock); row.addSpacing(16)

            # Connection status
            conn_dot = label("● Kết nối", "badge")
            conn_dot.setStyleSheet("background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; border-radius: 10px; padding: 4px 12px; font-size: 11px; font-weight: 700;")
            row.addWidget(conn_dot); row.addSpacing(12)

            # User
            uname_txt = getattr(self.user, 'username', '')
            user_btn = label(f"◉  {uname_txt}", bold=True)
            user_btn.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: 700;")
            row.addWidget(user_btn)
            return bar

        def go(self, key: str) -> None:
            self.stack.setCurrentWidget(self.pages[key]); self.breadcrumb.setText({"overview":"Tổng quan hệ thống", "operations":"Vận hành làn xe", "sessions":"Phiên gửi xe", "shifts":"Ca làm việc", "subscribers":"Quản lý thuê bao", "cards":"Quản lý thẻ xe", "fees":"Quản lý biểu phí", "lanes":"Cấu hình làn xe", "vehicle_types":"Cấu hình loại xe", "alerts":"Cảnh báo", "accounts":"Tài khoản & phân quyền", "settings":"Cài đặt hệ thống", "hardware":"Kết nối & Cài đặt thiết bị thật"}[key])
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
            self._apply_interaction_cursors(new_page)
            self.go(key)

        def page(self) -> tuple[QWidget, QVBoxLayout]:
            page = QWidget(); page.setObjectName("page")
            box = QVBoxLayout(page); box.setContentsMargins(24, 20, 24, 20); box.setSpacing(14)
            return page, box

        def _apply_interaction_cursors(self, root: QWidget) -> None:
            """Give every interactive control the same clear affordance."""
            for control in root.findChildren(QPushButton):
                control.setCursor(Qt.CursorShape.PointingHandCursor)
            for control in root.findChildren(QComboBox):
                control.setCursor(Qt.CursorShape.PointingHandCursor)

        def card(self, caption: str, value: str = "—") -> tuple[QFrame, QLabel]:
            frame = QFrame(); frame.setObjectName("card"); box = QVBoxLayout(frame); box.setContentsMargins(18, 16, 18, 16); box.addWidget(label(caption, "metricCaption")); number = label(value, "metricValue", True); box.addWidget(number); return frame, number

        def overview_page(self) -> QWidget:
            page, box = self.page()
            box.setContentsMargins(24, 20, 24, 20)
            box.setSpacing(16)

            # ── Metric cards row ──────────────────────────────────────
            cards_row = QHBoxLayout(); cards_row.setSpacing(12)
            metric_defs = [
                ("Xe đang trong bãi", "2", "0% công suất (60 chỗ giới hạn chỗ)", "🚙", "#2563eb"),
                ("Lượt vào hôm nay", "0", "Ra: 0", "↪", "#16a34a"),
                ("Doanh thu hôm nay", "0 đ", "Tháng: 0 đ", "💵", "#ea580c"),
                ("Cảnh báo chờ xử lý", "0", "Xem và xử lý →", "⚠", "#dc2626"),
            ]
            self.overview_values = []
            self.overview_sub_labels = []
            for title_txt, init_val, subtitle, icon, bg in metric_defs:
                card = QFrame()
                card.setStyleSheet(f"QFrame {{ background: {bg}; border-radius: 12px; border: none; }}")
                card.setMinimumHeight(142)
                card_box = QVBoxLayout(card); card_box.setContentsMargins(18, 16, 18, 16); card_box.setSpacing(4)
                top_row = QHBoxLayout()
                ttl = label(title_txt)
                ttl.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 12px; font-weight: 600;")
                top_row.addWidget(ttl); top_row.addStretch()
                icon_lbl = label(icon)
                icon_lbl.setStyleSheet("color: rgba(255,255,255,0.30); font-size: 28px;")
                top_row.addWidget(icon_lbl)
                card_box.addLayout(top_row)
                val_lbl = label(init_val, bold=True)
                val_lbl.setStyleSheet("color: white; font-size: 30px; font-weight: 800;")
                card_box.addWidget(val_lbl)
                # progress bar for first card
                if title_txt == "Xe đang trong bãi":
                    prog = QProgressBar(); prog.setRange(0, 60); prog.setValue(2)
                    prog.setFixedHeight(6)
                    prog.setStyleSheet(f"QProgressBar {{ background: rgba(255,255,255,0.25); border: none; border-radius: 3px; }} QProgressBar::chunk {{ background: white; border-radius: 3px; }}")
                    card_box.addWidget(prog)
                    self.overview_progress = prog
                sub_lbl = label(subtitle)
                sub_lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px;")
                card_box.addWidget(sub_lbl)
                self.overview_values.append(val_lbl)
                self.overview_sub_labels.append(sub_lbl)
                cards_row.addWidget(card, 1)
            box.addLayout(cards_row)

            # ── Middle row: Lane status  |  Revenue chart ────────────
            mid_row = QHBoxLayout(); mid_row.setSpacing(12)

            # Left: Lane status panel
            lane_panel = QFrame(); lane_panel.setObjectName("panel")
            lane_layout = QVBoxLayout(lane_panel); lane_layout.setContentsMargins(16, 14, 16, 14); lane_layout.setSpacing(8)
            lane_header = QHBoxLayout()
            lane_title_lbl = label("🚦 Trạng thái làn xe", bold=True)
            lane_title_lbl.setStyleSheet("font-size: 14px;")
            lane_header.addWidget(lane_title_lbl); lane_header.addStretch()
            refresh_icon = icon_btn("fa5s.sync-alt", "", _BTN_PLAIN_STYLE, 14)
            refresh_icon.setFixedSize(30, 30)
            refresh_icon.clicked.connect(self.refresh_live)
            operate_btn = QPushButton("Vận hành")
            operate_btn.setObjectName("primary")
            operate_btn.setStyleSheet("QPushButton { padding: 6px 16px; font-weight: 700; }")
            operate_btn.clicked.connect(lambda: self.go("operations"))
            lane_header.addWidget(refresh_icon); lane_header.addWidget(operate_btn)
            lane_layout.addLayout(lane_header)

            self.overview_lane_rows = []
            try: lanes_data = asyncio.run(_lanes(settings))
            except Exception: lanes_data = []
            for lane in lanes_data:
                row_w = QFrame()
                row_w.setStyleSheet("QFrame { background: #ffffff; border-radius: 8px; border: none; }")
                row_lay = QHBoxLayout(row_w); row_lay.setContentsMargins(12, 8, 12, 8); row_lay.setSpacing(10)
                # direction arrow
                arrow = "→" if lane.direction == "IN" else ("←" if lane.direction == "OUT" else "⇄")
                arrow_lbl = label(arrow)
                arrow_color = "#16a34a" if lane.direction == "IN" else ("#dc2626" if lane.direction == "OUT" else "#ea580c")
                arrow_lbl.setStyleSheet(f"color: {arrow_color}; font-size: 18px; font-weight: bold;")
                arrow_lbl.setFixedWidth(24)
                row_lay.addWidget(arrow_lbl)
                info_col = QVBoxLayout(); info_col.setSpacing(1)
                name_lbl = label(lane.name, bold=True)
                name_lbl.setStyleSheet("font-size: 13px;")
                sub_lbl2 = label("0 xe • 4 thiết bị")
                sub_lbl2.setStyleSheet("color: #64748b; font-size: 11px;")
                info_col.addWidget(name_lbl); info_col.addWidget(sub_lbl2)
                row_lay.addLayout(info_col, 1)
                status_badge = label("Chờ xe", "badge")
                status_badge.setStyleSheet("background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; border-radius: 10px; padding: 3px 10px; font-size: 11px;")
                row_lay.addWidget(status_badge)
                lane_layout.addWidget(row_w)
                if lane != lanes_data[-1]:
                    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                    sep.setStyleSheet("border: none; border-top: 1px solid #f1f5f9;")
                    lane_layout.addWidget(sep)
                self.overview_lane_rows.append((sub_lbl2, status_badge))
            if not lanes_data:
                lane_layout.addWidget(label("Chưa có làn hoạt động.", "muted"))
            lane_layout.addStretch()
            mid_row.addWidget(lane_panel, 2)

            # Right: Revenue chart (placeholder)
            chart_panel = QFrame(); chart_panel.setObjectName("panel")
            chart_layout = QVBoxLayout(chart_panel); chart_layout.setContentsMargins(16, 14, 16, 14); chart_layout.setSpacing(8)
            chart_header = QHBoxLayout()
            chart_title = label("◱  Doanh thu theo giờ", bold=True)
            chart_title.setStyleSheet("font-size: 14px;")
            chart_header.addWidget(chart_title); chart_header.addStretch()
            btn_day = QPushButton("Hôm nay")
            btn_day.setStyleSheet("background: #64748b; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            btn_week = QPushButton("Tuần")
            btn_week.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            def set_chart_period(period: str) -> None:
                active, inactive = (btn_day, btn_week) if period == "day" else (btn_week, btn_day)
                active.setStyleSheet("background: #64748b; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
                inactive.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            btn_day.clicked.connect(lambda: set_chart_period("day"))
            btn_week.clicked.connect(lambda: set_chart_period("week"))
            chart_header.addWidget(btn_day); chart_header.addWidget(btn_week)
            chart_layout.addLayout(chart_header)

            # A lightweight grid keeps the revenue scale understandable before data is present.
            chart_area = QFrame()
            chart_area.setStyleSheet("background: white; border-radius: 8px; border: none;")
            chart_area.setMinimumHeight(245)
            chart_inner = QGridLayout(chart_area); chart_inner.setContentsMargins(6, 6, 6, 2); chart_inner.setSpacing(0)
            for row, value in enumerate(range(10, -1, -1)):
                y_label = label("1" if value == 10 else ("0" if value == 0 else f"0.{value}"))
                y_label.setStyleSheet("color: #64748b; font-size: 9px;")
                y_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                chart_inner.addWidget(y_label, row, 0)
                line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;")
                chart_inner.addWidget(line, row, 1)
                chart_inner.setRowStretch(row, 1)
            hour_row = QHBoxLayout(); hour_row.setSpacing(0)
            for h in range(24):
                h_lbl = label(f"{h}h")
                h_lbl.setStyleSheet("color: #94a3b8; font-size: 9px;")
                h_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                hour_row.addWidget(h_lbl, 1)
            chart_inner.addLayout(hour_row, 11, 1)
            chart_inner.setColumnStretch(1, 1)
            chart_layout.addWidget(chart_area, 1)
            mid_row.addWidget(chart_panel, 3)
            box.addLayout(mid_row)

            # ── Bottom row: Active vehicles table  |  Breakdown + stats ─
            bot_row = QHBoxLayout(); bot_row.setSpacing(12)

            # Left: Active vehicles table
            veh_panel = QFrame(); veh_panel.setObjectName("panel")
            veh_layout = QVBoxLayout(veh_panel); veh_layout.setContentsMargins(16, 14, 16, 14); veh_layout.setSpacing(8)
            veh_header = QHBoxLayout()
            veh_title = label("🚗 Xe đang trong bãi", bold=True)
            veh_title.setStyleSheet("font-size: 14px;")
            veh_header.addWidget(veh_title); veh_header.addStretch()
            see_all_btn = QPushButton("Xem tất cả")
            see_all_btn.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            see_all_btn.clicked.connect(lambda: self.go("sessions"))
            veh_header.addWidget(see_all_btn)
            veh_layout.addLayout(veh_header)

            self.live_table = QTableWidget(0, 6)
            self.live_table.setHorizontalHeaderLabels(["BIỂN SỐ", "LOẠI XE", "VÀO LÚC", "THỜI GIAN", "LOẠI", "LÀN"])
            self.live_table.setAlternatingRowColors(True)
            self.live_table.setShowGrid(False)
            self.live_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.live_table.verticalHeader().setVisible(False)
            self.live_table.setMinimumHeight(160)
            self.live_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            hdr = self.live_table.horizontalHeader()
            for i in range(6): hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            self.live_table.setStyleSheet(
                "QTableWidget { border: 1px solid #e2e8f0; background: white; border-radius: 8px; }"
                "QHeaderView::section { background: #f8fafc; color: #64748b; font-size: 10px; font-weight: 700; border: none; border-bottom: 1px solid #e2e8f0; padding: 8px; }"
                "QTableWidget::item { padding: 8px 4px; border-bottom: 1px solid #f8fafc; }"
            )
            veh_layout.addWidget(self.live_table, 1)
            bot_row.addWidget(veh_panel, 2)

            # Right: Vehicle type breakdown + quick stats
            right_col = QVBoxLayout(); right_col.setSpacing(12)

            # Phân loại xe hôm nay
            breakdown_panel = QFrame(); breakdown_panel.setObjectName("panel")
            breakdown_layout = QVBoxLayout(breakdown_panel); breakdown_layout.setContentsMargins(16, 14, 16, 14); breakdown_layout.setSpacing(8)
            breakdown_title = label("🏍 Phân loại xe hôm nay", bold=True)
            breakdown_title.setStyleSheet("font-size: 14px;")
            breakdown_layout.addWidget(breakdown_title)
            self.overview_breakdown_lbl = label("Chưa có dữ liệu hôm nay.", "muted")
            self.overview_breakdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.overview_breakdown_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 20px;")
            breakdown_layout.addWidget(self.overview_breakdown_lbl, 1)
            right_col.addWidget(breakdown_panel, 1)

            # Thống kê nhanh
            stats_panel = QFrame(); stats_panel.setObjectName("panel")
            stats_layout = QVBoxLayout(stats_panel); stats_layout.setContentsMargins(16, 14, 16, 14); stats_layout.setSpacing(6)
            stats_title = label("⚡ Thống kê nhanh", bold=True)
            stats_title.setStyleSheet("font-size: 14px;")
            stats_layout.addWidget(stats_title)

            stat_defs = [
                ("👥 Thuê bao đang gửi",   "0"),
                ("🧑 Vãng lai đang gửi",   "0"),
                ("🚦 Làn đang hoạt động",   "0 / 0"),
                ("📡 Thiết bị online",      "0 / 0"),
            ]
            self.overview_stat_lbls = []
            for stat_text, init_val in stat_defs:
                stat_row = QHBoxLayout()
                stat_name = label(stat_text)
                stat_name.setStyleSheet("color: #475569; font-size: 12px;")
                stat_val = label(init_val, bold=True)
                stat_val.setStyleSheet("font-size: 13px; color: #0f172a;")
                stat_row.addWidget(stat_name); stat_row.addStretch(); stat_row.addWidget(stat_val)
                stats_layout.addLayout(stat_row)
                self.overview_stat_lbls.append(stat_val)
                # separator
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("border: none; border-top: 1px solid #f1f5f9;")
                stats_layout.addWidget(sep)
            right_col.addWidget(stats_panel)
            bot_row.addLayout(right_col, 1)
            box.addLayout(bot_row)
            return page

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
            
            # --- TCP RFID Hook ---
            def handle_rfid_scan(ip_addr: str, rfid_code: str):
                # Put the RFID code into the first lane's UID input
                for i in range(grid.count()):
                    item = grid.itemAt(i)
                    if item and item.widget():
                        w = item.widget()
                        # Find the first QLineEdit with placeholder "Ma the (UID)"
                        from PySide6.QtWidgets import QLineEdit
                        for le in w.findChildren(QLineEdit):
                            if "UID" in le.placeholderText():
                                le.setText(rfid_code)
                                # Automatically click the "Vao" or "Ra" button depending on direction?
                                # For MVP, we just fill the text and let operator click, or 
                                # trigger entry automatically if it's IN lane, exit if OUT lane.
                                # Let's just fill it for now.
                                return
                                
            # Connect the signal
            global_hw_signals.rfid_scanned.connect(handle_rfid_scan)

            
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
            
            summary = QFrame(); summary.setObjectName("softSurface")
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

        def make_table(self, headers: list[str], minimum_rows: int = 10, action_col_width: int = 300) -> QTableWidget:
            from PySide6.QtCore import Qt as _Qt
            table = QTableWidget(0, len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.setMinimumHeight(max(220, minimum_rows * 38))
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setCursor(Qt.CursorShape.PointingHandCursor)
            hdr = table.horizontalHeader()
            hdr.setMinimumSectionSize(120)
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
                    for c, value in enumerate(values):
                        item = QTableWidgetItem(str(value))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        table.setItem(r, c, item)
                table.resizeColumnsToContents()
            def filter_rows(query: str) -> None:
                for r in range(table.rowCount()): table.setRowHidden(r, bool(query) and query.lower() not in " ".join(table.item(r,c).text().lower() for c in range(table.columnCount()) if table.item(r,c)))
            refresh.clicked.connect(load); search.textChanged.connect(filter_rows); load(); return page

        def session_page(self) -> QWidget:
            page, box = self.page()
            
            # Header
            h = label("Phiên gửi xe", bold=True); h.setStyleSheet("font-size:24px;")
            box.addWidget(h)
            
            # Stats Card
            stat_frame = QFrame()
            stat_frame.setObjectName("stat_frame")
            stat_frame.setStyleSheet("QFrame#stat_frame { background: #ecfdf5; border: none; border-radius: 8px; }")
            stat_frame.setFixedSize(160, 80)
            stat_layout = QVBoxLayout(stat_frame)
            stat_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            val_lbl = label("0", bold=True)
            val_lbl.setStyleSheet("color: #22c55e; font-size: 28px;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            desc_lbl = label("Đang gửi")
            desc_lbl.setStyleSheet("color: #64748b; font-size: 14px;")
            desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            stat_layout.addWidget(val_lbl)
            stat_layout.addWidget(desc_lbl)
            box.addWidget(stat_frame)
            
            # Tabs
            tabs = QTabWidget()
            tabs.setStyleSheet("QTabWidget::pane { border: none; background: transparent; } QTabBar::tab { background: transparent; padding: 8px 16px; margin-right: 2px; color: #64748b; font-weight: 700; } QTabBar::tab:selected { color: #f97316; border-bottom: 2px solid #f97316; }")
            
            tab_active = QWidget(); tab_active_ly = QVBoxLayout(tab_active)
            tab_history = QWidget(); tab_history_ly = QVBoxLayout(tab_history)
            
            tabs.addTab(tab_active, "Đang trong bãi")
            tabs.addTab(tab_history, "Lịch sử")
            box.addWidget(tabs, 1)
            
            # --- Tab 1: Active ---
            tbl_active = self.make_table(["Thẻ", "Biển số", "Loại xe", "Loại", "Vào lúc", "Thời gian", "Làn vào", "Thao tác"], action_col_width=120)
            tab_active_ly.addWidget(tbl_active)
            
            # --- Tab 2: History ---
            hist_top = QHBoxLayout()
            from PySide6.QtWidgets import QDateEdit, QComboBox
            from PySide6.QtCore import QDate, QDateTime
            
            hist_top.addWidget(label("Từ ngày", "muted"))
            dt_from = QDateEdit(QDate.currentDate().addDays(-7))
            dt_from.setCalendarPopup(True)
            hist_top.addWidget(dt_from)
            
            hist_top.addWidget(label("Đến ngày", "muted"))
            dt_to = QDateEdit(QDate.currentDate())
            dt_to.setCalendarPopup(True)
            hist_top.addWidget(dt_to)
            
            hist_top.addWidget(label("Loại", "muted"))
            cb_type = QComboBox()
            cb_type.addItems(["Tất cả", "Vãng lai", "Thuê bao"])
            hist_top.addWidget(cb_type)
            
            hist_top.addWidget(label("Biển số", "muted"))
            search_plate = QLineEdit()
            search_plate.setPlaceholderText("VD: 51A...")
            hist_top.addWidget(search_plate)
            
            btn_search = QPushButton("Tìm")
            btn_search.setStyleSheet("QPushButton { background: #f97316; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; } QPushButton:hover { background: #ea580c; }")
            hist_top.addWidget(btn_search)
            
            hist_top.addStretch()
            total_lbl = label("Tổng: 0 phiên", bold=True)
            total_lbl.setStyleSheet("color: #64748b;")
            hist_top.addWidget(total_lbl)
            
            tab_history_ly.addLayout(hist_top)
            
            tbl_history = self.make_table(["Thẻ", "Biển số vào", "Biển số ra", "Loại", "Vào", "Ra", "Thời gian", "Phí", "Trạng thái"], action_col_width=120)
            tab_history_ly.addWidget(tbl_history)
            
            def load_sessions():
                try:
                    db = Database(settings.local_database_url)
                    import asyncio
                    from pmql.infrastructure.persistence.sqlite.repositories import SQLiteSessionRepository, SQLiteVehicleRepository, SQLiteLaneRepository
                    
                    async def fetch():
                        async with db.session() as session:
                            s_repo = SQLiteSessionRepository(session)
                            l_repo = SQLiteLaneRepository(session)
                            
                            all_sessions = await s_repo.list_recent(settings.branch_id, 5000)
                            lanes = await l_repo.list_active()
                            l_map = {l.id: l.name for l in lanes}
                            
                            return all_sessions, l_map
                    
                    v_map = asyncio.run(_vehicle_name_map(settings))
                    all_sessions, l_map = asyncio.run(fetch())
                    
                    active = [s for s in all_sessions if s.status == "ACTIVE"]
                    val_lbl.setText(str(len(active)))
                    
                    # Populate Active
                    tbl_active.setRowCount(len(active))
                    from PySide6.QtGui import QColor as _QC
                    for r, s in enumerate(active):
                        card_lbl = label(s.rfid_card_id or "-", bold=True)
                        card_lbl.setStyleSheet("color: #ef4444;")
                        tbl_active.setCellWidget(r, 0, card_lbl)
                        
                        plate_lbl = label(s.plate_number or "-", bold=True)
                        plate_lbl.setStyleSheet("background: #fef08a; border: 1px solid #facc15; border-radius: 4px; padding: 2px 6px; color: #1e293b;")
                        plate_w = QWidget(); p_ly = QHBoxLayout(plate_w); p_ly.setContentsMargins(0,0,0,0); p_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); p_ly.addWidget(plate_lbl)
                        tbl_active.setCellWidget(r, 1, plate_w)
                        
                        v_name = v_map.get(s.vehicle_type, "Xe máy") if hasattr(s, 'vehicle_type') else "Xe máy"
                        v_icon = "🛵" if "máy" in v_name.lower() else "🚗"
                        v_lbl = label(f"{v_icon} {v_name}")
                        v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        tbl_active.setCellWidget(r, 2, v_lbl)
                        
                        type_badge = label("Thuê bao" if s.subscriber_id else "Vãng lai")
                        type_badge.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px 6px; color: #475569; font-size: 11px;")
                        type_w = QWidget(); ty_ly = QHBoxLayout(type_w); ty_ly.setContentsMargins(0,0,0,0); ty_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); ty_ly.addWidget(type_badge)
                        tbl_active.setCellWidget(r, 3, type_w)
                        
                        entry_str = s.entry_time.strftime("%H:%M:%S %d/%m/%Y")
                        e_lbl = label(entry_str)
                        e_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        tbl_active.setCellWidget(r, 4, e_lbl)
                        
                        now = QDateTime.currentDateTime().toPython()
                        mins = int((now - s.entry_time).total_seconds() / 60)
                        hrs, mins = divmod(mins, 60)
                        dur_lbl = label(f"{hrs}g {mins}p", bold=True)
                        dur_lbl.setStyleSheet("background: #38bdf8; color: white; border-radius: 4px; padding: 2px 6px;")
                        dur_w = QWidget(); d_ly = QHBoxLayout(dur_w); d_ly.setContentsMargins(0,0,0,0); d_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); d_ly.addWidget(dur_lbl)
                        tbl_active.setCellWidget(r, 5, dur_w)
                        
                        l_name = l_map.get(s.lane_in_id, "Làn vào")
                        ln_lbl = label(l_name)
                        ln_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        tbl_active.setCellWidget(r, 6, ln_lbl)
                        
                        btn_exc = QPushButton("Ngoại lệ")
                        btn_exc.setStyleSheet("QPushButton { color: #ef4444; background: white; border: 1px solid #ef4444; border-radius: 4px; padding: 2px 8px; }")
                        b_w = QWidget(); b_ly = QHBoxLayout(b_w); b_ly.setContentsMargins(0,0,0,0); b_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); b_ly.addWidget(btn_exc)
                        tbl_active.setCellWidget(r, 7, b_w)
                        
                    # Populate History
                    start_d = dt_from.date().toPython()
                    end_d = dt_to.date().toPython()
                    search_str = search_plate.text().strip().lower()
                    
                    history = []
                    for s in all_sessions:
                        if s.status == "ACTIVE": continue
                        if s.entry_time.date() < start_d or s.entry_time.date() > end_d: continue
                        if search_str and search_str not in (s.plate_number or "").lower(): continue
                        history.append(s)
                        
                    total_lbl.setText(f"Tổng: {len(history)} phiên")
                    tbl_history.setRowCount(len(history))
                    for r, s in enumerate(history):
                        card_lbl = label(s.rfid_card_id or "-", bold=True); card_lbl.setStyleSheet("color: #ef4444;")
                        tbl_history.setCellWidget(r, 0, card_lbl)
                        
                        plate_lbl = label(s.plate_number or "-", bold=True); plate_lbl.setStyleSheet("background: #fef08a; border: 1px solid #facc15; border-radius: 4px; padding: 2px 6px; color: #1e293b;")
                        plate_w = QWidget(); p_ly = QHBoxLayout(plate_w); p_ly.setContentsMargins(0,0,0,0); p_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); p_ly.addWidget(plate_lbl)
                        tbl_history.setCellWidget(r, 1, plate_w)
                        
                        plate_out_lbl = label(s.plate_number or "-", bold=True); plate_out_lbl.setStyleSheet("background: #fef08a; border: 1px solid #facc15; border-radius: 4px; padding: 2px 6px; color: #1e293b;")
                        plate_out_w = QWidget(); p2_ly = QHBoxLayout(plate_out_w); p2_ly.setContentsMargins(0,0,0,0); p2_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); p2_ly.addWidget(plate_out_lbl)
                        tbl_history.setCellWidget(r, 2, plate_out_w)
                        
                        type_badge = label("Thuê bao" if s.subscriber_id else "Vãng lai")
                        type_badge.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px 6px; color: #475569; font-size: 11px;")
                        type_w = QWidget(); ty_ly = QHBoxLayout(type_w); ty_ly.setContentsMargins(0,0,0,0); ty_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); ty_ly.addWidget(type_badge)
                        tbl_history.setCellWidget(r, 3, type_w)
                        
                        e_lbl = label(s.entry_time.strftime("%H:%M:%S %d/%m/%Y")); e_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        tbl_history.setCellWidget(r, 4, e_lbl)
                        
                        ex_lbl = label(s.exit_time.strftime("%H:%M:%S %d/%m/%Y") if s.exit_time else "-"); ex_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        tbl_history.setCellWidget(r, 5, ex_lbl)
                        
                        dur_str = "-"
                        if s.exit_time:
                            mins = int((s.exit_time - s.entry_time).total_seconds() / 60)
                            hrs, mins = divmod(mins, 60)
                            dur_str = f"{hrs}g {mins}p"
                        tbl_history.setItem(r, 6, QTableWidgetItem(dur_str))
                        tbl_history.item(r, 6).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        fee_str = f"{s.fee_amount:,} đ" if s.fee_amount else "-"
                        tbl_history.setItem(r, 7, QTableWidgetItem(fee_str))
                        tbl_history.item(r, 7).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        
                        status_badge = label("Đã ra")
                        status_badge.setStyleSheet("background: #dcfce7; border: 1px solid #86efac; border-radius: 4px; padding: 2px 6px; color: #166534; font-size: 11px;")
                        st_w = QWidget(); st_ly = QHBoxLayout(st_w); st_ly.setContentsMargins(0,0,0,0); st_ly.setAlignment(Qt.AlignmentFlag.AlignCenter); st_ly.addWidget(status_badge)
                        tbl_history.setCellWidget(r, 8, st_w)
                        
                except Exception as exc:
                    print("Error loading sessions:", exc)
            
            load_sessions()
            btn_search.clicked.connect(load_sessions)
            
            return page

        def shift_page(self) -> QWidget:
            page, box = self.page(); heading = QHBoxLayout(); title = label("Quản lý ca làm việc", bold=True); title.setStyleSheet("font-size:24px; color: #1e293b;"); heading.addWidget(title); heading.addStretch(); box.addLayout(heading)
            
            tabs = QTabWidget(); box.addWidget(tabs, 1)
            tabs.setStyleSheet("QTabWidget::pane { border: none; border-top: 1px solid #e0e7f0; top: -1px; } QTabBar::tab { background: transparent; color: #94a3b8; padding: 12px 20px; font-weight: 700; font-size: 14px; border: none; border-bottom: 2px solid transparent; margin-right: 4px; } QTabBar::tab:selected { color: #f97316; border-bottom: 2px solid #f97316; } QTabBar::tab:hover { color: #1e293b; }")

            current_tab = QWidget(); current_layout = QVBoxLayout(current_tab); current_layout.setAlignment(Qt.AlignmentFlag.AlignTop); current_layout.setContentsMargins(0, 20, 0, 0)
            self.current_shift_banner = QFrame(); self.current_shift_banner.setObjectName("card"); self.current_shift_banner.setStyleSheet("#card { background: #ecfdf5; border: none; border-radius: 12px; padding: 24px; }")
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
            
            self.btn_open_shift = QPushButton("▶ Mở ca làm việc"); self.btn_open_shift.setObjectName("success"); self.btn_open_shift.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_open_shift.setStyleSheet("QPushButton { padding: 10px 24px; font-size: 14px; font-weight: bold; }"); self.btn_open_shift.clicked.connect(self.open_shift)
            self.btn_close_shift = QPushButton("■ Đóng ca"); self.btn_close_shift.setObjectName("danger"); self.btn_close_shift.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_close_shift.setStyleSheet("QPushButton { padding: 10px 24px; font-size: 14px; font-weight: bold; }"); self.btn_close_shift.clicked.connect(self.close_shift); self.btn_close_shift.hide()
            
            btn_layout = QVBoxLayout(); btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
            btn_layout.addWidget(self.btn_open_shift); btn_layout.addWidget(self.btn_close_shift)
            banner_top_row.addLayout(btn_layout); banner_layout.addLayout(banner_top_row)
            
            self.stats_grid = QGridLayout(); self.stats_grid.setSpacing(16); self.stats_grid.setContentsMargins(0, 16, 0, 0)
            
            def make_stat_card(num_color, icon_text):
                f = QFrame(); f.setStyleSheet("background: white; border: none; border-radius: 8px; padding: 16px;")
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
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE); edit.clicked.connect(lambda _=False, item=s: self.edit_shift(item)); actions_row.addWidget(edit)
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE); remove.clicked.connect(lambda _=False, item=s: self.delete_shift(item)); actions_row.addWidget(remove)
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
                self.shift_id = s.id
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
            container.setStyleSheet("QFrame#main_container { background: #ffffff; border-radius: 12px; border: none; }")
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
            
            combo_style = "QComboBox { min-height: 24px; }"
            
            lane_combo = QComboBox(); lane_combo.addItem("-- Tất cả làn --", None); lane_combo.setStyleSheet(combo_style)
            try:
                for ln in asyncio.run(_lanes(settings)): lane_combo.addItem(ln.name, ln.id)
            except: pass
            
            type_combo = QComboBox(); type_combo.setStyleSheet(combo_style)
            for st in shift_types: type_combo.addItem(f"{st['name']} ({st['time']})", st)
            type_combo.addItem("Khác", {"name": "Khác", "time": "", "hours": ""}); type_combo.setEditable(True)
            
            cash_combo = QComboBox(); cash_combo.setStyleSheet(combo_style); cash_combo.addItems(["Không có tiền đầu ca", "500,000", "1,000,000", "2,000,000"]); cash_combo.setEditable(True)
            note_combo = QComboBox(); note_combo.setStyleSheet(combo_style); note_combo.addItems(["-- Không có ghi chú --", "Bàn giao chìa khóa", "Hệ thống lỗi nhẹ"]); note_combo.setEditable(True)
            
            summary_box = QFrame(); summary_box.setStyleSheet("background: #eff6ff; border-radius: 8px; padding: 16px; margin-top: 10px; border: none;")
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
                        btn.setStyleSheet("#card_frame { background: #fff7ed; border: none; border-radius: 8px; } QLabel { color: #f97316; border: none; }")
                        btn.n.setStyleSheet("font-size: 14px; background: transparent; color: #ea580c; border: none;")
                        btn.t.setStyleSheet("font-size: 11px; background: transparent; color: #ea580c; border: none;")
                        btn.h.setStyleSheet("font-size: 11px; background: transparent; font-weight: bold; color: #ea580c; border: none;")
                    else:
                        btn.setStyleSheet("#card_frame { background: #ffffff; border: none; border-radius: 8px; } QLabel { color: #64748b; border: none; }")
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
            container.setStyleSheet("QFrame#main_container { background: #ffffff; border-radius: 12px; border: none; }")
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
                w = QFrame(); w.setStyleSheet(f"background: {bg_color}; border: none; border-radius: 6px;")
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
            combo_style = "QComboBox { min-height: 24px; }"
            input_style = "QLineEdit { min-height: 24px; }"
            
            lbl_cash = label("Tiền mặt thực tế cuối ca"); lbl_cash.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            closing_cash = QComboBox(); closing_cash.setStyleSheet(combo_style)
            closing_cash.addItems([f"{s.opening_cash + s.total_revenue:,} đ", "0 đ", "Nhập số tiền khác..."])
            
            custom_cash = QLineEdit(); custom_cash.setPlaceholderText("Nhập số tiền VNĐ"); custom_cash.setStyleSheet(input_style); custom_cash.hide()
            
            lbl_note = label("Ghi chú bàn giao"); lbl_note.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
            close_note = QComboBox(); close_note.setEditable(True); close_note.setStyleSheet(combo_style)
            close_note.addItems(["-- Không có ghi chú --"])
            
            form.addRow(lbl_cash); form.addRow(closing_cash); form.addRow(custom_cash); form.addRow(lbl_note); form.addRow(close_note)
            content.addLayout(form)
            
            recon_box = QFrame(); recon_box.setObjectName("recon_box"); recon_box.setStyleSheet("#recon_box { background: #f8fafc; border: none; border-radius: 6px; margin: 16px 24px 8px 24px; }")
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
                f.setStyleSheet(
                    f"QFrame#fee_card {{ background: {'#fffbeb' if is_active else '#ffffff'}; border: none;"
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
                sep.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;"); c.addWidget(sep)

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
                
                sep2_f = QFrame(); sep2_f.setFrameShape(QFrame.Shape.HLine); sep2_f.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;"); c.addWidget(sep2_f)

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
            calc_frame.setStyleSheet("QFrame#calc_frame { background: white; border: none; border-radius: 8px; }")
            calc_layout = QVBoxLayout(calc_frame)
            calc_layout.setContentsMargins(20, 16, 20, 16)
            
            calc_title = label("🧮 Tính phí thử", bold=True)
            calc_title.setStyleSheet("color: #d97706; font-size: 14px;")
            calc_layout.addWidget(calc_title)
            
            sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
            sep3.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;"); calc_layout.addWidget(sep3)

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
                        calc_obj = _FC()
                        fee = calc_obj.calculate(entry, exit_, rule_c)
                        hours, mins = divmod(minutes, 60)
                        
                        result_lbl.setStyleSheet("color: #16a34a; font-size: 14px; font-weight: bold;")
                        result_lbl.setText(f"Tổng phí: {int(getattr(fee, 'amount', fee)):,} đ (Áp dụng: {rule_c.name} - Thời gian gửi: {hours} giờ {mins} phút)")
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
            self.card_table = self.make_table(["Mã thẻ (UID)", "Loại thẻ", "Thuê bao", "Trạng thái", "Thao tác"], action_col_width=250); box.addWidget(self.card_table, 1); self.load_cards(); return page

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
                
                status_btn = icon_btn("fa5s.sync", "Đổi TT", _BTN_PLAIN_STYLE)
                
                def _show_status_menu(item_card=card, btn=status_btn):
                    from PySide6.QtWidgets import QMenu
                    from PySide6.QtCore import QPoint
                    menu = QMenu(self.card_table)
                    menu.setStyleSheet("QMenu { background: white; border: 1px solid #cbd5e1; border-radius: 6px; } QMenu::item { padding: 6px 24px; } QMenu::item:selected { background: #f1f5f9; }")
                    for text, val in [("Có sẵn", "AVAILABLE"), ("Đang dùng", "IN_USE"), ("Đã mất", "LOST"), ("Bị khóa", "LOCKED")]:
                        action = menu.addAction(text)
                        action.triggered.connect(lambda _, v=val, c=item_card: _change_card_status(v, c))
                    menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))
                    
                def _change_card_status(val, item_card):
                    try:
                        asyncio.run(_update_card(settings, item_card.id, item_card.card_type, item_card.subscriber_id, val))
                        self.reload_page("cards")
                    except Exception as e:
                        QMessageBox.warning(self, "Lỗi", str(e))
                status_btn.clicked.connect(lambda _=False: _show_status_menu())
                
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                edit.clicked.connect(lambda _=False, item=card: self.edit_card(item))
                remove.clicked.connect(lambda _=False, item=card: self.delete_card(item))
                actions_row.addWidget(status_btn); actions_row.addWidget(edit); actions_row.addWidget(remove)
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
                card.setStyleSheet("QFrame#card { background: white; border: none; border-radius: 8px; }")
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
                dev_style = "background: #f0fdf4; color: #16a34a; border: none; border-radius: 6px; padding: 4px 8px; font-size: 11px;"
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
                edit = icon_btn("fa5s.edit", "Sửa cấu hình", _BTN_EDIT_STYLE)
                edit.setStyleSheet("background: white; border: 1px solid #93c5fd; color: #2563eb; border-radius: 6px; padding: 8px; font-weight: bold;")
                edit.clicked.connect(lambda _=False, item=lane: self.edit_lane(item))
                
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                remove.setStyleSheet("background: white; border: 1px solid #fca5a5; color: #dc2626; border-radius: 6px; padding: 8px 14px;")
                remove.clicked.connect(lambda _=False, item=lane: self.delete_lane(item))
                
                actions.addWidget(edit, 1)
                actions.addWidget(remove)
                cbox.addLayout(actions)
                
                self.lane_grid.addWidget(card, index // 2, index % 2)

        def show_lane_modal(self, lane=None):
            title = "Thêm làn xe" if not lane else "Sửa làn xe"
            dialog, content, footer = modal_shell(self, title, 520)
            form = QFormLayout(); content.addLayout(form)
            name = QLineEdit(lane.name if lane else "")
            name.setPlaceholderText("Ví dụ: Làn vào 1, Làn ra A")
            direction = QComboBox(); direction.addItem("Xe vào", "IN"); direction.addItem("Xe ra", "OUT"); direction.addItem("Hai chiều", "BIDIRECTIONAL")
            status = QComboBox(); status.addItem("Hoạt động", True); status.addItem("Tắt", False)
            if lane:
                direction.setCurrentIndex(max(0, direction.findData(lane.direction)))
                status.setCurrentIndex(0 if lane.is_active else 1)
            form.addRow("Tên làn *", name); form.addRow("Chiều xe", direction); form.addRow("Trạng thái", status)
            hint = label("Thiết bị có thể được gán ở mục Kết nối thiết bị sau khi lưu làn.", "muted")
            hint.setWordWrap(True); content.addWidget(hint)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu cấu hình")
            save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            camera = lane.camera_source if lane else "cam1"
            rfid = lane.rfid_device_id if lane else "rfid1"
            barrier = lane.barrier_device_id if lane else "bar1"
            
            def do_save():
                try:
                    is_active = bool(status.currentData())
                    selected_dir = direction.currentData()
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
            vehicle_group.setStyleSheet("QGroupBox { margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #475569; }")
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
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE); remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
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

        def settings_page(self) -> QWidget:
            page, box = self.page(); h = label("Cài đặt hệ thống", bold=True); h.setStyleSheet("font-size:24px;"); box.addWidget(h)
            
            try:
                import asyncio
                sys_settings = asyncio.run(_load_sys_settings(settings))
            except Exception as e:
                print("Error loading sys settings:", e)
                sys_settings = None
                
            main_layout = QHBoxLayout(); main_layout.setSpacing(24)
            left_col = QVBoxLayout(); left_col.setSpacing(16)
            right_col = QVBoxLayout(); right_col.setSpacing(16)
            
            # --- Cột trái ---
            def make_group(title_text, icon_text, color):
                g = QFrame(); g.setStyleSheet(f"QFrame {{ background: white; border: none; border-radius: 8px; }}")
                ly = QVBoxLayout(g); ly.setSpacing(16)
                
                header = QHBoxLayout()
                ico = label(icon_text, bold=True)
                ico.setStyleSheet(f"background: {color}20; color: {color}; border-radius: 4px; padding: 4px 8px; border: none;")
                header.addWidget(ico)
                
                t_ly = QVBoxLayout(); t_ly.setSpacing(2)
                t_lbl = label(title_text, bold=True); t_lbl.setStyleSheet("border: none;")
                t_ly.addWidget(t_lbl)
                header.addLayout(t_ly)
                header.addStretch()
                ly.addLayout(header)
                return g, ly
                
            # 1. Thông tin bãi xe
            g1, l1 = make_group("Thông tin bãi xe", "🏢", "#f97316")
            f1 = QGridLayout(); f1.setSpacing(12)
            f1.addWidget(label("Tên bãi xe *", "muted"), 0, 0)
            in_name = QLineEdit(sys_settings.parking_name if sys_settings else "")
            f1.addWidget(in_name, 1, 0)
            
            f1.addWidget(label("Số điện thoại", "muted"), 0, 1)
            in_phone = QLineEdit(sys_settings.phone if sys_settings else "")
            f1.addWidget(in_phone, 1, 1)
            
            f1.addWidget(label("Địa chỉ", "muted"), 2, 0, 1, 2)
            in_address = QLineEdit(sys_settings.address if sys_settings else "")
            f1.addWidget(in_address, 3, 0, 1, 2)
            
            f1.addWidget(label("Dòng chữ cuối vé (footer)", "muted"), 4, 0, 1, 2)
            in_footer = QLineEdit(sys_settings.footer_text if sys_settings else "")
            f1.addWidget(in_footer, 5, 0, 1, 2)
            l1.addLayout(f1); left_col.addWidget(g1)
            
            # 2. Sức chứa
            g2, l2 = make_group("Sức chứa bãi xe", "📉", "#3b82f6")
            f2 = QGridLayout(); f2.setSpacing(12)
            f2.addWidget(label("🚗 Tổng cộng", "muted"), 0, 0)
            in_cap_total = QLineEdit(str(sys_settings.capacity_total if sys_settings else 0))
            f2.addWidget(in_cap_total, 1, 0)
            
            f2.addWidget(label("🛵 Xe máy", "muted"), 0, 1)
            in_cap_moto = QLineEdit(str(sys_settings.capacity_moto if sys_settings else 0))
            f2.addWidget(in_cap_moto, 1, 1)
            
            f2.addWidget(label("🚗 Ô tô", "muted"), 0, 2)
            in_cap_car = QLineEdit(str(sys_settings.capacity_car if sys_settings else 0))
            f2.addWidget(in_cap_car, 1, 2)
            
            f2.addWidget(label("🚚 Xe tải", "muted"), 0, 3)
            in_cap_truck = QLineEdit(str(sys_settings.capacity_truck if sys_settings else 0))
            f2.addWidget(in_cap_truck, 1, 3)
            l2.addLayout(f2); left_col.addWidget(g2)
            
            # 3. Thông số vận hành
            g3, l3 = make_group("Thông số vận hành", "⚙️", "#22c55e")
            f3 = QGridLayout(); f3.setSpacing(12)
            f3.addWidget(label("Tự đóng barrier sau (giây)", "muted"), 0, 0)
            in_barrier = QLineEdit(str(sys_settings.auto_barrier_delay_sec if sys_settings else 8))
            f3.addWidget(in_barrier, 1, 0)
            
            f3.addWidget(label("Thời gian miễn phí (phút)", "muted"), 0, 1)
            in_free = QLineEdit(str(sys_settings.free_time_mins if sys_settings else 5))
            f3.addWidget(in_free, 1, 1)
            
            f3.addWidget(label("Ngưỡng tin cậy ANPR", "muted"), 0, 2)
            in_anpr = QLineEdit(str(sys_settings.anpr_threshold if sys_settings else 0.7))
            f3.addWidget(in_anpr, 1, 2)
            
            from PySide6.QtWidgets import QTimeEdit
            from PySide6.QtCore import QTime
            f3.addWidget(label("Phụ thu đêm từ", "muted"), 2, 0)
            in_n_from = QTimeEdit()
            if sys_settings and sys_settings.night_surcharge_from:
                in_n_from.setTime(QTime.fromString(sys_settings.night_surcharge_from, "HH:mm"))
            f3.addWidget(in_n_from, 3, 0)
            
            f3.addWidget(label("Phụ thu đêm đến", "muted"), 2, 1)
            in_n_to = QTimeEdit()
            if sys_settings and sys_settings.night_surcharge_to:
                in_n_to.setTime(QTime.fromString(sys_settings.night_surcharge_to, "HH:mm"))
            f3.addWidget(in_n_to, 3, 1)
            
            f3.addWidget(label("Port TCP Gateway", "muted"), 2, 2)
            in_tcp = QLineEdit(str(sys_settings.tcp_port if sys_settings else 9001))
            f3.addWidget(in_tcp, 3, 2)
            l3.addLayout(f3); left_col.addWidget(g3)
            
            # 4. Thanh toán QR
            g4, l4 = make_group("Thanh toán QR / Ngân hàng", "🪪", "#a855f7")
            f4 = QGridLayout(); f4.setSpacing(12)
            f4.addWidget(label("Ngân hàng", "muted"), 0, 0)
            in_bank = QComboBox(); in_bank.addItems(["Chọn ngân hàng", "Vietcombank", "Techcombank", "MBBank", "BIDV"])
            if sys_settings and sys_settings.bank_name: in_bank.setCurrentText(sys_settings.bank_name)
            f4.addWidget(in_bank, 1, 0)
            
            f4.addWidget(label("Số tài khoản", "muted"), 0, 1)
            in_acc = QLineEdit(sys_settings.bank_account_number if sys_settings else "")
            f4.addWidget(in_acc, 1, 1)
            
            f4.addWidget(label("Tên chủ tài khoản", "muted"), 0, 2)
            in_owner = QLineEdit(sys_settings.bank_account_name if sys_settings else "")
            f4.addWidget(in_owner, 1, 2)
            l4.addLayout(f4); left_col.addWidget(g4)
            
            # 5. Thông báo cảnh báo
            g5, l5 = make_group("Thông báo cảnh báo", "🔔", "#ef4444")
            f5 = QGridLayout(); f5.setSpacing(12)
            f5.addWidget(label("Email nhận cảnh báo", "muted"), 0, 0)
            in_email = QLineEdit(sys_settings.alert_email if sys_settings else "")
            f5.addWidget(in_email, 1, 0)
            l5.addLayout(f5); left_col.addWidget(g5)
            
            # Action buttons
            btn_ly = QHBoxLayout(); btn_ly.addStretch()
            btn_reset = QPushButton("Đặt lại")
            btn_reset.setStyleSheet("background: white; border: 1px solid #cbd5e1; padding: 8px 16px; border-radius: 4px;")
            btn_ly.addWidget(btn_reset)
            
            btn_save = QPushButton("Lưu cài đặt")
            btn_save.setStyleSheet("background: #f97316; color: white; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
            btn_ly.addWidget(btn_save)
            
            def on_save():
                data = {
                    "parking_name": in_name.text(),
                    "phone": in_phone.text(),
                    "address": in_address.text(),
                    "footer_text": in_footer.text(),
                    "capacity_total": int(in_cap_total.text() or 0),
                    "capacity_moto": int(in_cap_moto.text() or 0),
                    "capacity_car": int(in_cap_car.text() or 0),
                    "capacity_truck": int(in_cap_truck.text() or 0),
                    "auto_barrier_delay_sec": int(in_barrier.text() or 8),
                    "free_time_mins": int(in_free.text() or 5),
                    "anpr_threshold": float(in_anpr.text() or 0.7),
                    "night_surcharge_from": in_n_from.time().toString("HH:mm"),
                    "night_surcharge_to": in_n_to.time().toString("HH:mm"),
                    "tcp_port": int(in_tcp.text() or 9001),
                    "bank_name": in_bank.currentText(),
                    "bank_account_number": in_acc.text(),
                    "bank_account_name": in_owner.text(),
                    "alert_email": in_email.text()
                }
                asyncio.run(_save_sys_settings(settings, data))
                QMessageBox.information(self, "Thành công", "Đã lưu cài đặt hệ thống!")
                
            btn_save.clicked.connect(on_save)
            left_col.addLayout(btn_ly)
            left_col.addStretch()
            
            # --- Cột phải ---
            def make_stat_row(lbl, val, color="#1e293b"):
                r = QHBoxLayout()
                r.addWidget(label(lbl, "muted"))
                r.addStretch()
                v = label(val, bold=True)
                v.setStyleSheet(f"color: {color}; border: none;")
                r.addWidget(v)
                return r
                
            rg1, rl1 = make_group("Thông tin hệ thống", "ℹ️", "#f97316")
            rl1.addLayout(make_stat_row("Phiên bản", "1.0.0"))
            sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine); sep1.setStyleSheet("color: #e2e8f0; border: none; border-top: 1px solid #e2e8f0;"); rl1.addWidget(sep1)
            rl1.addLayout(make_stat_row("Cơ sở dữ liệu", "SQLite"))
            sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet("color: #e2e8f0; border: none; border-top: 1px solid #e2e8f0;"); rl1.addWidget(sep2)
            rl1.addLayout(make_stat_row("TCP Gateway", "port 9001"))
            sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine); sep3.setStyleSheet("color: #e2e8f0; border: none; border-top: 1px solid #e2e8f0;"); rl1.addWidget(sep3)
            rl1.addLayout(make_stat_row("API Server", "Đang chạy", "#16a34a"))
            right_col.addWidget(rg1)
            
            rg2, rl2 = make_group("Thống kê dữ liệu", "📊", "#f97316")
            
            try:
                import asyncio
                from pmql.infrastructure.persistence.sqlite.repositories import SQLiteSessionRepository
                
                async def fetch_stats():
                    db = Database(settings.local_database_url)
                    try:
                        async with db.session() as session:
                            s_repo = SQLiteSessionRepository(session)
                            all_sessions = await s_repo.list_recent(settings.branch_id, 5000)
                            
                            active_count = sum(1 for s in all_sessions if s.status == "ACTIVE")
                            from datetime import date
                            today_count = sum(1 for s in all_sessions if s.entry_time.date() == date.today())
                            return active_count, today_count
                    finally:
                        await db.dispose()
                        
                active_count, today_count = asyncio.run(fetch_stats())
            except:
                active_count, today_count = 0, 0
                
            rl2.addLayout(make_stat_row("Xe trong bãi", str(active_count)))
            sep4 = QFrame(); sep4.setFrameShape(QFrame.Shape.HLine); sep4.setStyleSheet("color: #e2e8f0; border: none; border-top: 1px solid #e2e8f0;"); rl2.addWidget(sep4)
            rl2.addLayout(make_stat_row("Lượt hôm nay", str(today_count)))
            sep5 = QFrame(); sep5.setFrameShape(QFrame.Shape.HLine); sep5.setStyleSheet("color: #e2e8f0; border: none; border-top: 1px solid #e2e8f0;"); rl2.addWidget(sep5)
            rl2.addLayout(make_stat_row("Phiên bản DB", "SQLite 3"))
            right_col.addWidget(rg2)
            
            rg3, rl3 = make_group("Công suất hiện tại", "⚡", "#f97316")
            if sys_settings and sys_settings.capacity_total > 0:
                percent = int((active_count / sys_settings.capacity_total) * 100) if sys_settings.capacity_total > 0 else 0
                lbl = label(f"Đã dùng {percent}% ({active_count}/{sys_settings.capacity_total})")
            else:
                lbl = label("Không giới hạn")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("border: none;")
            rl3.addWidget(lbl)
            right_col.addWidget(rg3)
            
            rg4, rl4 = make_group("Sao lưu & Xuất", "💾", "#f97316")
            btn_export = QPushButton("Xuất cài đặt (JSON)")
            btn_export.setStyleSheet("background: white; border: 1px solid #3b82f6; color: #3b82f6; padding: 6px; border-radius: 4px; font-weight: bold;")
            rl4.addWidget(btn_export)
            
            btn_import = QPushButton("Nhập cài đặt")
            btn_import.setStyleSheet("background: white; border: 1px solid #cbd5e1; color: #475569; padding: 6px; border-radius: 4px; font-weight: bold;")
            rl4.addWidget(btn_import)
            
            btn_api = QPushButton("API Documentation")
            btn_api.setStyleSheet("background: white; border: 1px solid #cbd5e1; color: #475569; padding: 6px; border-radius: 4px; font-weight: bold;")
            rl4.addWidget(btn_api)
            right_col.addWidget(rg4)
            
            right_col.addStretch()
            
            scroll_ly = QHBoxLayout()
            left_w = QWidget(); left_w.setLayout(left_col); scroll_ly.addWidget(left_w, 7)
            right_w = QWidget(); right_w.setLayout(right_col); scroll_ly.addWidget(right_w, 3)
            
            scroll_content = QWidget(); scroll_content.setLayout(scroll_ly)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(scroll_content)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            box.addWidget(scroll, 1)
            
            return page

        def hardware_page(self) -> QWidget:
            page, box = self.page()
            title = label("Kết nối & Cài đặt thiết bị thật", bold=True)
            title.setStyleSheet("font-size:24px;")
            box.addWidget(title)

            # Device type definitions
            DEVICE_TYPES = [
                ("rfid",    "🪪",  "Đầu đọc thẻ",  "RFID / NFC",        "#3b82f6",
                 [("TCP Socket","Kết nối IP trực tiếp"), ("Wiegand","Wiegand 26/34 bit"), ("RS485 Serial","USB-RS485 adapter")]),
                ("camera",  "📷", "Camera ANPR",  "Nhận dạng biển số",  "#f59e0b",
                 [("RTSP Stream","IP Camera qua mạng LAN"), ("HTTP API","SDK HTTP Dahua/Hikvision"), ("USB Camera","Camera USB/Webcam")]),
                ("finger",  "👆", "Vân tay",       "Nhận dạng sinh trắc","#a855f7",
                 [("SDK TCP","ZKTeco qua mạng"), ("RS485/UART","Module vân tay serial"), ("USB Module","Module USB vân tay")]),
                ("barrier", "🚧", "Barrier",       "Barie tự động",       "#22c55e",
                 [("RS485 Modbus","Barrier qua RS485"), ("RS232 Serial","Cổng serial COM"), ("Relay GPIO","Relay board / Arduino"), ("TCP IP","Barrier có IP")]),
            ]

            import asyncio

            # ── Right panel ─────────────────────────────────────────────────
            right_w = QWidget(); right_w.setFixedWidth(280)
            right_col = QVBoxLayout(right_w); right_col.setContentsMargins(0,0,0,0); right_col.setSpacing(12)

            def section_box(icon, title_text, color):
                f = QFrame(); f.setStyleSheet("QFrame { background: white; border: none; border-radius: 8px; }")
                v = QVBoxLayout(f); v.setContentsMargins(14,12,14,12); v.setSpacing(6)
                h = QHBoxLayout()
                ico_lbl = label(icon); ico_lbl.setStyleSheet(f"background:{color}20;color:{color};border:none;border-radius:4px;padding:3px 7px;")
                h.addWidget(ico_lbl); t = label(title_text, bold=True); t.setStyleSheet("border:none;"); h.addWidget(t); h.addStretch()
                v.addLayout(h); return f, v

            sdk_f, sdk_v = section_box("📦", "SDK & Thư viện hỗ trợ", "#f97316")
            for line in ["• SDK TCP (ZKTeco, Hikvision, Dahua)","• Thư viện: python-aiougent, evdev",""]:
                l = label(line); l.setStyleSheet("color:#475569;font-size:11px;border:none;"); l.setWordWrap(True); sdk_v.addWidget(l)
            for tag, items in [("📷 Camera ANPR", ["• RTSP stream → OpenCV → AI model","• HTTP API (Dahua, Hikvision SDK)","• ONVIF → RTSP capture"]),
                                ("👆 Vân tay", ["• ZKTeco SDK (hỗ trợ Python)","• UART/RS485 → USB adapter","• FP template lưu trong DB"]),
                                ("🚧 Barrier / Barie", ["• RS485 Modbus RTU","• RS232 Serial protocol","• Relay output (GPIO / USB relay)"])]:
                h2 = label(tag, bold=True); h2.setStyleSheet("color:#1e293b;font-size:12px;border:none;margin-top:6px;"); sdk_v.addWidget(h2)
                for it in items:
                    l2 = label(it); l2.setStyleSheet("color:#475569;font-size:11px;border:none;"); sdk_v.addWidget(l2)
            right_col.addWidget(sdk_f)

            # Connected devices panel
            conn_f, conn_v = section_box("🔌", "Thiết bị đang kết nối", "#22c55e")
            refresh_btn = QPushButton("⟳"); refresh_btn.setFixedSize(28,28)
            refresh_btn.setStyleSheet("border:none;border-radius:14px;background:#f1f5f9;font-weight:bold;padding:0;")
            conn_f.layout().itemAt(0).layout().addWidget(refresh_btn)

            devices_list_lbl = label("", "muted"); devices_list_lbl.setWordWrap(True)

            def refresh_devices():
                try:
                    devs = asyncio.run(_list_devices(settings))
                    if devs:
                        lines = []
                        for d in devs:
                            icon_map = {"rfid":"🪪","camera":"📷","finger":"👆","barrier":"🚧"}
                            ico = icon_map.get(d.device_type, "📡")
                            lines.append(f"{ico} {d.name}")
                        devices_list_lbl.setText("\n".join(lines))
                    else:
                        devices_list_lbl.setText("Chưa có thiết bị nào kết nối\nHoặc kết nối TCP qua cổng 9001")
                except: devices_list_lbl.setText("Chưa có thiết bị nào kết nối")

            refresh_devices()
            refresh_btn.clicked.connect(refresh_devices)
            conn_v.addWidget(devices_list_lbl)

            check_btn = QPushButton("⟳ Kiểm tra lại")
            check_btn.setStyleSheet("background:white;border:1px solid #cbd5e1;border-radius:6px;padding:6px 14px;color:#475569;font-weight:600;")
            check_btn.clicked.connect(refresh_devices)
            conn_v.addWidget(check_btn)

            note = label("ℹ Chi hiển thị thiết bị đang kết nối TCP thực tế vào cổng 9001")
            note.setStyleSheet("color:#94a3b8;font-size:11px;border:none;")
            note.setWordWrap(True)
            conn_v.addWidget(note)
            right_col.addWidget(conn_f)
            right_col.addStretch()

            # ── Left panel ──────────────────────────────────────────────────
            left_w = QWidget()
            left_col = QVBoxLayout(left_w); left_col.setContentsMargins(0,0,0,0); left_col.setSpacing(16)

            selected_type = [None]     # mutable ref
            selected_proto = [None]
            device_card_refs = {}
            proto_btn_refs = []

            # Step section helper
            def step_frame(num, title_text):
                f = QFrame(); f.setStyleSheet("QFrame { background: white; border: none; border-radius: 8px; }")
                v = QVBoxLayout(f); v.setContentsMargins(16,14,16,14); v.setSpacing(10)
                h = QHBoxLayout(); h.setSpacing(10)
                badge = label(str(num), bold=True)
                badge.setFixedSize(28,28)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet("background:#f97316;color:white;border-radius:14px;border:none;font-size:13px;font-weight:700;")
                h.addWidget(badge)
                t = label(title_text, bold=True); t.setStyleSheet("font-size:14px;border:none;"); h.addWidget(t); h.addStretch()
                v.addLayout(h)
                return f, v

            # ── Step 1 — Chọn loại thiết bị ─────────────────────────────
            s1_frame, s1_v = step_frame(1, "Chọn loại thiết bị cần kết nối")
            card_row = QHBoxLayout(); card_row.setSpacing(12)

            proto_section_frame_ref = [None]
            proto_label_ref = [None]
            proto_btn_row_ref = [None]

            def make_device_card(key, icon, name, sub, color, protos):
                card = QFrame()
                card.setObjectName(f"devcard_{key}")
                card.setFixedWidth(150); card.setFixedHeight(120)
                card.setCursor(Qt.CursorShape.PointingHandCursor)
                card.setStyleSheet("QFrame { background: white; border: none; border-radius: 10px; }")
                v = QVBoxLayout(card); v.setContentsMargins(10,10,10,10); v.setAlignment(Qt.AlignmentFlag.AlignCenter)

                ico_lbl = label(icon); ico_lbl.setStyleSheet(f"font-size:28px;border:none;background:{color}15;border-radius:8px;padding:6px 10px;")
                ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                n_lbl = label(name, bold=True); n_lbl.setStyleSheet("border:none;font-size:12px;"); n_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                s_lbl = label(sub, "muted"); s_lbl.setStyleSheet("color:#94a3b8;font-size:11px;border:none;"); s_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                v.addWidget(ico_lbl); v.addWidget(n_lbl); v.addWidget(s_lbl)

                def on_click(_, k=key, c=color, ps=protos, nm=name):
                    selected_type[0] = k; selected_proto[0] = None
                    for ck, cf in device_card_refs.items():
                        if ck == k:
                            cf.setStyleSheet(f"QFrame {{ background: {c}10; border: none; border-radius: 10px; }}")
                        else:
                            cf.setStyleSheet("QFrame { background: white; border: none; border-radius: 10px; }")
                    # Update protocol section
                    if proto_label_ref[0]: proto_label_ref[0].setText(nm)
                    if proto_btn_row_ref[0]:
                        layout = proto_btn_row_ref[0]
                        while layout.count(): layout.takeAt(0).widget().deleteLater() if layout.itemAt(0) and layout.itemAt(0).widget() else layout.takeAt(0)
                        proto_btn_refs.clear()
                        for p_name, p_sub in ps:
                            pb = QPushButton(f"{p_name}\n{p_sub}")
                            pb.setCheckable(True)
                            pb.setStyleSheet("QPushButton{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:6px 14px;font-size:12px;color:#475569;}"
                                             "QPushButton:checked{background:#fff7ed;border:2px solid #f97316;color:#ea580c;font-weight:700;}")
                            def on_proto(chk, pn=p_name, pb_ref=pb):
                                selected_proto[0] = pn
                                for rb in proto_btn_refs:
                                    if rb is not pb_ref: rb.setChecked(False)
                            pb.clicked.connect(on_proto)
                            layout.addWidget(pb)
                            proto_btn_refs.append(pb)
                        layout.addStretch()

                class ClickFrame(type(card)):
                    def mousePressEvent(self, ev): on_click(True)
                card.__class__ = ClickFrame
                device_card_refs[key] = card
                return card

            for key, icon, name, sub, color, protos in DEVICE_TYPES:
                card_row.addWidget(make_device_card(key, icon, name, sub, color, protos))
            card_row.addStretch()
            s1_v.addLayout(card_row)
            left_col.addWidget(s1_frame)

            # ── Step 2 — Chọn giao thức ──────────────────────────────────
            s2_frame, s2_v = step_frame(2, "Chọn giao thức kết nối")
            s2_h = s2_frame.layout().itemAt(0).layout()
            proto_lbl = label("—", "muted"); proto_lbl.setStyleSheet("color:#94a3b8;font-size:12px;border:none;")
            s2_h.addWidget(proto_lbl); proto_label_ref[0] = proto_lbl

            note2 = label("Chọn giao thức phù hợp với thiết bị của bạn:"); note2.setStyleSheet("color:#64748b;font-size:12px;border:none;")
            s2_v.addWidget(note2)
            proto_row = QHBoxLayout(); proto_row.setSpacing(10)
            proto_btn_row_ref[0] = proto_row
            proto_row.addStretch()
            s2_v.addLayout(proto_row)
            left_col.addWidget(s2_frame)

            # ── Step 3 — Gán làn xe ──────────────────────────────────────
            s3_frame, s3_v = step_frame(3, "Gán thiết bị vào làn xe")
            s3_grid = QGridLayout(); s3_grid.setSpacing(16)

            s3_grid.addWidget(label("Chọn làn xe", "muted"), 0, 0)
            lane_combo = QComboBox(); lane_combo.addItem("— Chọn làn —")
            try:
                for ln in asyncio.run(_lanes(settings)): lane_combo.addItem(ln.name, ln.id)
            except: pass
            s3_grid.addWidget(lane_combo, 1, 0)

            s3_grid.addWidget(label("Tên thiết bị (tùy chọn)", "muted"), 0, 1)
            name_edit = QLineEdit(); name_edit.setPlaceholderText("VD: Camera làn 1 vào")
            s3_grid.addWidget(name_edit, 1, 1)
            s3_v.addLayout(s3_grid)
            left_col.addWidget(s3_frame)

            # ── Step 4 — Test & Lưu ─────────────────────────────────────
            s4_frame, s4_v = step_frame(4, "Kiểm tra kết nối và lưu cấu hình")
            s4_h = QHBoxLayout(); s4_h.setSpacing(12)

            test_btn = QPushButton("⚡ Test kết nối")
            test_btn.setStyleSheet("background:white;border:1px solid #3b82f6;color:#3b82f6;border-radius:6px;padding:8px 18px;font-weight:700;")
            save_btn = QPushButton("💾 Lưu thiết bị")
            save_btn.setStyleSheet("background:#f97316;color:white;border:none;border-radius:6px;padding:8px 18px;font-weight:700;")

            status_lbl = label(""); status_lbl.setStyleSheet("border:none;")

            def on_test():
                if not selected_type[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn loại thiết bị trước."); return
                if not selected_proto[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn giao thức kết nối."); return
                status_lbl.setText("⏳ Đang kiểm tra..."); status_lbl.setStyleSheet("color:#f59e0b;border:none;")
                # Simulate test result (mock)
                status_lbl.setText("✅ Mô phỏng thành công (Mock mode)"); status_lbl.setStyleSheet("color:#16a34a;border:none;")

            def on_save():
                if not selected_type[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn loại thiết bị."); return
                if not selected_proto[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn giao thức kết nối."); return
                lane_id = lane_combo.currentData() or ""
                dev_name = name_edit.text().strip()
                try:
                    asyncio.run(_save_device(settings, selected_type[0], selected_proto[0], lane_id, dev_name))
                    QMessageBox.information(page, "Đã lưu", f"Thiết bị đã được lưu thành công!")
                    refresh_devices()
                except Exception as e:
                    QMessageBox.critical(page, "Lỗi", str(e))

            test_btn.clicked.connect(on_test)
            save_btn.clicked.connect(on_save)
            s4_h.addWidget(test_btn); s4_h.addWidget(save_btn); s4_h.addWidget(status_lbl); s4_h.addStretch()
            s4_v.addLayout(s4_h)
            left_col.addWidget(s4_frame)

            # ── Resources section ────────────────────────────────────────
            res_f = QFrame(); res_f.setStyleSheet("QFrame { background: white; border: none; border-radius: 8px; }")
            res_v = QVBoxLayout(res_f); res_v.setContentsMargins(16,14,16,14); res_v.setSpacing(12)
            res_h0 = QHBoxLayout()
            res_ico = label("📦"); res_ico.setStyleSheet("background:#f97316;color:white;border:none;border-radius:4px;padding:3px 7px;font-size:14px;")
            res_h0.addWidget(res_ico); t2 = label("Tài nguyên & Driver mẫu", bold=True); t2.setStyleSheet("border:none;"); res_h0.addWidget(t2); res_h0.addStretch()
            res_v.addLayout(res_h0)
            cards_h = QHBoxLayout(); cards_h.setSpacing(12)
            for icon, title_r, sub_r, color_r in [
                ("🐍","Driver Python TCP","Tải liệu PDF - client TCP","#3b82f6"),
                ("🔷","Arduino / ESP32","Tải liệu PDF - RFID TCP","#22c55e"),
                ("🍓","Raspberry Pi","Tải liệu PDF - Pi + Camera","#ef4444"),
                ("📄","Tài liệu giao thức","PDF - TCP Protocol full","#f97316"),
            ]:
                rc = QFrame(); rc.setStyleSheet("QFrame{background:#f8fafc;border-radius:8px;border:none;}")
                rv = QVBoxLayout(rc); rv.setContentsMargins(12,12,12,12); rv.setSpacing(6)
                ri = label(icon); ri.setStyleSheet(f"font-size:22px;background:{color_r}15;border-radius:6px;padding:4px 8px;border:none;"); ri.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rv.addWidget(ri)
                rv.addWidget(label(title_r, bold=True))
                rv.addWidget(label(sub_r, "muted"))
                rb = QPushButton("📥 Xuất PDF")
                rb.setStyleSheet(f"background:{color_r};color:white;border:none;border-radius:4px;padding:5px;font-weight:600;font-size:11px;")
                rv.addWidget(rb); cards_h.addWidget(rc)
            res_v.addLayout(cards_h); left_col.addWidget(res_f)
            left_col.addStretch()

            # ── Assemble main layout ─────────────────────────────────────
            main_h = QHBoxLayout(); main_h.setSpacing(20)
            scroll_w = QScrollArea(); scroll_w.setWidgetResizable(True); scroll_w.setFrameShape(QFrame.Shape.NoFrame)
            scroll_w.setWidget(left_w); main_h.addWidget(scroll_w, 1); main_h.addWidget(right_w)
            content_w = QWidget(); content_w.setLayout(main_h)
            box.addWidget(content_w, 1)
            return page


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
            dialog, box, footer = modal_shell(self, "Vai trò và quyền", 600)
            dialog.setMinimumHeight(520)
            box.addWidget(label("Tạo hoặc chỉnh sửa vai trò", bold=True)); selector = QComboBox(); selector.addItem("+ Vai trò mới"); name, description = QLineEdit(), QLineEdit(); name.setPlaceholderText("Tên vai trò, ví dụ: CASHIER"); description.setPlaceholderText("Mô tả vai trò")
            permissions = QListWidget()
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
            cancel, save_button = QPushButton("Hủy"), QPushButton("Lưu vai trò"); save_button.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save_button); cancel.clicked.connect(dialog.reject)
            def save() -> None:
                if not name.text().strip(): QMessageBox.warning(dialog, "Thiếu tên", "Nhập tên vai trò."); return
                codes = {permissions.item(i).data(Qt.ItemDataRole.UserRole) for i in range(permissions.count()) if permissions.item(i).checkState() == Qt.CheckState.Checked}
                try: asyncio.run(_save_role(settings, name.text().strip().upper(), description.text().strip(), codes)); dialog.accept()
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save_button.clicked.connect(save); dialog.exec()

        def open_shift(self) -> None:
            dialog, content, footer = modal_shell(self, "Mở ca làm việc", 740)
            content.addWidget(label("Chọn ca làm việc", "muted"))
            preset_layout = QHBoxLayout()
            from PySide6.QtSvgWidgets import QSvgWidget
            svg_m = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>'
            svg_a = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 18a5 5 0 0 0-10 0"></path><line x1="12" y1="9" x2="12" y2="2"></line><line x1="4.22" y1="10.22" x2="5.64" y2="11.64"></line><line x1="1" y1="18" x2="3" y2="18"></line><line x1="21" y1="18" x2="23" y2="18"></line><line x1="18.36" y1="10.22" x2="19.78" y2="11.64"></line><line x1="23" y1="22" x2="1" y2="22"></line><polyline points="16 6 12 2 8 6"></polyline></svg>'
            svg_n = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
            svg_f = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>'
            presets = [("Ca sáng", "06:00 - 14:00", "8 tiếng", svg_m), ("Ca chiều", "14:00 - 22:00", "8 tiếng", svg_a), ("Ca đêm", "22:00 - 06:00", "8 tiếng", svg_n), ("Ca ngày đủ", "07:00 - 19:00", "12 tiếng", svg_f)]
            self.selected_preset = presets[0]
            preset_buttons = []
            for name, time, dur, icon in presets:
                btn = QPushButton(); btn.setCheckable(True)
                btn.setMinimumHeight(130)
                btn.setStyleSheet("QPushButton { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; } QPushButton:checked { background: #fff7ed; border-color: #ea580c; }")
                vbox = QVBoxLayout(btn)
                icon_lbl = QSvgWidget()
                icon_lbl.load(icon.encode('utf-8'))
                icon_lbl.setFixedSize(32, 32)
                icon_cont = QWidget(); icon_lay = QHBoxLayout(icon_cont); icon_lay.setContentsMargins(0,0,0,0); icon_lay.setAlignment(Qt.AlignmentFlag.AlignCenter); icon_lay.addWidget(icon_lbl)
                name_lbl = label(name, bold=True); name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); time_lbl = label(time, "muted"); time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dur_lbl = label(dur); dur_lbl.setStyleSheet("color:#f97316; font-size:11px;"); dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                vbox.addWidget(icon_cont); vbox.addWidget(name_lbl); vbox.addWidget(time_lbl); vbox.addWidget(dur_lbl)
                def on_click(checked, p=(name, time, dur, icon), button=btn):
                    if checked:
                        for b in preset_buttons:
                            if b != button: b.setChecked(False)
                        self.selected_preset = p; update_summary()
                btn.clicked.connect(on_click); preset_buttons.append(btn); preset_layout.addWidget(btn)
            preset_buttons[0].setChecked(True); content.addLayout(preset_layout); content.addSpacing(15)
            grid = QGridLayout()
            grid.addWidget(label("Làn phụ trách", "muted"), 0, 0); lane_cb = QComboBox(); lane_cb.addItem("-- Tất cả làn --")
            lanes = []
            try:
                lanes = asyncio.run(_lanes(settings))
                for ln in lanes: lane_cb.addItem(ln.name)
            except Exception: pass
            grid.addWidget(lane_cb, 1, 0); grid.addWidget(label("Loại ca", "muted"), 0, 1); type_cb = QComboBox()
            for name, time, _, _ in presets: type_cb.addItem(f"{name} ({time})")
            grid.addWidget(type_cb, 1, 1); grid.addWidget(label("Tiền đầu ca (VNĐ)", "muted"), 2, 0); cash_cb = QComboBox(); cash_cb.addItems(["Không có tiền đầu ca", "500.000 đ", "1.000.000 đ", "2.000.000 đ", "5.000.000 đ", "Số tiền khác..."])
            grid.addWidget(cash_cb, 3, 0); grid.addWidget(label("Ghi chú bổ sung", "muted"), 2, 1); note_cb = QComboBox(); note_cb.addItems(["-- Không có ghi chú --", "Bàn giao với ca trước", "Bàn giao cho ca sau", "Thiết bị cần kiểm tra", "Có sự cố cần báo cáo", "Ngày lễ - lưu lượng cao", "Ca cuối tuần"])
            grid.addWidget(note_cb, 3, 1); content.addLayout(grid); content.addSpacing(15)
            summary_frame = QFrame(); summary_frame.setStyleSheet("background: #f8fafc; border-radius: 8px; border: none;")
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
                    self.shift_id = asyncio.run(_open_shift(settings, getattr(self.user, "user_id"), lane_id=lane_id, opening_cash=start_cash, note=note_txt))
                except Exception as exc: QMessageBox.warning(dialog, "Không thể mở ca", str(exc)); return
                self.shift_status_badge.setText("Ca đang hoạt động"); self.shift_status_badge.setStyleSheet("background: #dcfce7; color: #166534; border: 1px solid #bbf7d0;")
                self.shift_button.setText("✓ Ca đang hoạt động")
                self.refresh_live(); self.reload_page("shifts"); dialog.accept()
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
                active_cnt = stats['active']
                today_cnt = stats['today_count']
                revenue = stats['revenue']
                alerts_cnt = stats.get('alerts', 0)
                if len(self.overview_values) >= 4:
                    self.overview_values[0].setText(str(active_cnt))
                    self.overview_values[1].setText(str(today_cnt))
                    self.overview_values[2].setText(f"{revenue:,} đ")
                    self.overview_values[3].setText(str(alerts_cnt))
                if len(self.overview_sub_labels) >= 4:
                    cap = 60
                    pct = int(active_cnt / cap * 100) if cap else 0
                    self.overview_sub_labels[0].setText(f"{pct}% công suất ({cap} chỗ giới hạn chỗ)")
                    self.overview_sub_labels[1].setText(f"Ra: {today_cnt}")
                if hasattr(self, 'overview_progress'):
                    self.overview_progress.setValue(min(active_cnt, 60))
                # Populate active vehicles table
                plates = stats.get("plates", [])
                sessions_detail = stats.get("sessions_detail", [])
                self.live_table.setRowCount(len(sessions_detail) if sessions_detail else len(plates))
                if sessions_detail:
                    for r, sess in enumerate(sessions_detail):
                        plate_item = QTableWidgetItem(sess.get("plate", "RFID"))
                        plate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        vtype_item = QTableWidgetItem("🏍 " + sess.get("vehicle_type", "—"))
                        entry_item = QTableWidgetItem(sess.get("entry_time", "—"))
                        entry_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        duration_item = QTableWidgetItem(sess.get("duration", "—"))
                        duration_item.setForeground(__import__('PySide6.QtGui', fromlist=['QColor']).QColor("#2563eb"))
                        duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        type_item = QTableWidgetItem("Vãng lai")
                        type_item.setForeground(__import__('PySide6.QtGui', fromlist=['QColor']).QColor("#16a34a"))
                        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        lane_item = QTableWidgetItem("—")
                        lane_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.live_table.setItem(r, 0, plate_item)
                        self.live_table.setItem(r, 1, vtype_item)
                        self.live_table.setItem(r, 2, entry_item)
                        self.live_table.setItem(r, 3, duration_item)
                        self.live_table.setItem(r, 4, type_item)
                        self.live_table.setItem(r, 5, lane_item)
                else:
                    for r, plate in enumerate(plates):
                        for c, val in enumerate((plate, "Xe máy", "Hôm nay", "—", "Vãng lai", "—")):
                            it = QTableWidgetItem(val); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.live_table.setItem(r, c, it)
                # Quick stats
                if hasattr(self, "overview_stat_lbls") and len(self.overview_stat_lbls) >= 4:
                    sub_cnt = stats.get('subscriber_count', 0)
                    guest_cnt = active_cnt - sub_cnt if active_cnt >= sub_cnt else active_cnt
                    lane_total = stats.get('lane_total', 0)
                    lane_active = stats.get('lane_active', 0)
                    self.overview_stat_lbls[0].setText(str(sub_cnt))
                    self.overview_stat_lbls[1].setText(str(guest_cnt))
                    self.overview_stat_lbls[2].setText(f"{lane_active} / {lane_total}")
                    self.overview_stat_lbls[3].setText(f"0 / 0")

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
            sessions = await SQLiteSessionRepository(session).list_recent(settings.branch_id, 500)
            users = await SQLiteUserRepository(session).list_all()
            lanes = await SQLiteLaneRepository(session).list_active(settings.branch_id)
        active = [s for s in sessions if s.status == "ACTIVE"]
        today = date.today()
        closed = [s for s in sessions if s.exit_time and s.exit_time.date() == today]
        # Build sessions_detail for live table
        now = datetime.now()
        def fmt_duration(entry_time):
            diff = now - entry_time
            h = int(diff.total_seconds() // 3600)
            m = int((diff.total_seconds() % 3600) // 60)
            return f"{h}g {m}p" if h else f"{m}p"
        sessions_detail = []
        for s in active:
            sessions_detail.append({
                "plate": s.plate_number or "RFID",
                "vehicle_type": getattr(s, 'vehicle_type', 'Xe máy'),
                "entry_time": s.entry_time.strftime("%H:%M:%S %d/%m/%Y"),
                "duration": fmt_duration(s.entry_time),
            })
        return {
            "active": len(active),
            "plates": [s.plate_number for s in active if s.plate_number],
            "sessions_detail": sessions_detail,
            "today_count": len([s for s in sessions if s.entry_time.date() == today]),
            "revenue": sum(s.fee_amount for s in closed),
            "users": len([u for u in users if u.is_active]),
            "subscriber_count": 0,
            "lane_total": len(lanes),
            "lane_active": len(lanes),
            "alerts": 0,
        }
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
async def _load_sys_settings(settings: Settings):
    db = Database(settings.local_database_url)
    try:
        from pmql.infrastructure.persistence.sqlite.repositories import SQLiteSettingsRepository
        async with db.session() as session:
            return await SQLiteSettingsRepository(session).get_settings()
    finally:
        await db.dispose()

async def _save_sys_settings(settings: Settings, data: dict):
    db = Database(settings.local_database_url)
    try:
        from pmql.infrastructure.persistence.sqlite.repositories import SQLiteSettingsRepository
        async with db.session() as session:
            await SQLiteSettingsRepository(session).save_settings(data)
    finally:
        await db.dispose()

async def _list_devices(settings: Settings):
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    from sqlalchemy import select
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            rows = (await session.execute(select(DeviceModel).where(DeviceModel.branch_id == settings.branch_id))).scalars().all()
            return list(rows)
    finally:
        await db.dispose()

async def _save_device(settings: Settings, device_type: str, protocol: str, lane_id: str, name: str):
    import uuid
    from datetime import datetime
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            dev = DeviceModel(
                id=str(uuid.uuid4()),
                branch_id=settings.branch_id,
                name=name or f"{device_type} - {protocol}",
                device_type=device_type,
                connection_string=f"protocol={protocol};lane={lane_id}",
                is_online=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                sync_version=1
            )
            session.add(dev)
    finally:
        await db.dispose()

async def _delete_device(settings: Settings, device_id: str):
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            dev = await session.get(DeviceModel, device_id)
            if dev:
                await session.delete(dev)
    finally:
        await db.dispose()
