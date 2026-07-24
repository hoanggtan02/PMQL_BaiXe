from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import datetime, date, timedelta
from pmql.ui.pages import *

class MainWindow(QMainWindow, DashboardPageMixin, OperationsPageMixin, SessionPageMixin, AlertPageMixin, ShiftPageMixin, SubscriberPageMixin, CardPageMixin, FeePageMixin, LanePageMixin, Vehicle_typePageMixin, UserPageMixin, SettingsPageMixin, DevicePageMixin):
    def __init__(self, user: object, settings) -> None:
            super().__init__()
            self.settings = settings; self.user = user; self.shift_id: str | None = None; self.nav: dict[str, QPushButton] = {}
            try: self.permission_codes = asyncio.run(_role_permissions(self.settings, getattr(user, "role")))
            except Exception: self.permission_codes = set()
            self.setWindowTitle("PMQL Bãi Xe – Quản trị vận hành"); self.setMinimumSize(1180, 720); self.setStyleSheet(LIGHT_THEME)
            root = QWidget(); root.setObjectName("root"); layout = QHBoxLayout(root); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
            layout.addWidget(self.build_sidebar()); right = QWidget(); right_layout = QVBoxLayout(right); right_layout.setContentsMargins(0, 0, 0, 0); right_layout.setSpacing(0)
            right_layout.addWidget(self.build_header()); self.stack = QStackedWidget(); right_layout.addWidget(self.stack); layout.addWidget(right, 1); self.setCentralWidget(root)
            self.page_factories = {"overview": self.overview_page, "operations": self.operations_page, "sessions": self.session_page, "shifts": self.shift_page, "subscribers": self.subscriber_page, "cards": self.card_page, "alerts": self.alert_page, "fees": self.fee_page, "lanes": self.lane_page, "vehicle_types": self.vehicle_type_page, "accounts": self.accounts_page, "self.settings": self.settings_page, "hardware": self.hardware_page}
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
                    ("self.settings",    "⚙  Cài đặt"),
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
            footer_lay = QHBoxLayout(footer_area); footer_lay.setContentsMargins(16, 12, 16, 16); footer_lay.setSpacing(12)
            
            # Avatar
            avatar = QLabel("".join([w[0].upper() for w in getattr(self.user, "full_name", "").split()][:2]))
            avatar.setFixedSize(36, 36)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet("background: #f97316; color: white; font-weight: bold; font-size: 14px; border-radius: 18px;")
            footer_lay.addWidget(avatar)
            
            # Text info
            text_lay = QVBoxLayout(); text_lay.setSpacing(2); text_lay.setContentsMargins(0, 0, 0, 0)
            uname = label(getattr(self.user, "full_name", ""), bold=True)
            uname.setStyleSheet("color: white; font-size: 13px; font-weight: 700;")
            text_lay.addWidget(uname)
            
            role_dict = {"admin": "Quản trị viên", "operator": "Nhân viên vận hành"}
            role_txt = role_dict.get(getattr(self.user, "role", ""), getattr(self.user, "role", ""))
            r_lbl = label(role_txt)
            r_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
            text_lay.addWidget(r_lbl)
            
            footer_lay.addLayout(text_lay, 1)
            
            # Logout btn
            logout_btn = icon_btn("fa5s.sign-out-alt", "")
            logout_btn.setFixedSize(32, 32)
            logout_btn.setStyleSheet("QPushButton { background: transparent; border: 1px solid #334155; color: #cbd5e1; border-radius: 6px; font-size: 14px; padding: 0; } QPushButton:hover { background: #1e293b; color: white; border: 1px solid #475569; }")
            logout_btn.setToolTip("Đăng xuất")
            
            def do_logout():
                from pmql.ui.login import Login
                self._login_window = Login(self.settings, type(self))
                self._login_window.show()
                self.close()
                
            logout_btn.clicked.connect(do_logout)
            footer_lay.addWidget(logout_btn)
            
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
            self.stack.setCurrentWidget(self.pages[key]); self.breadcrumb.setText({"overview":"Tổng quan hệ thống", "operations":"Vận hành làn xe", "sessions":"Phiên gửi xe", "shifts":"Ca làm việc", "subscribers":"Quản lý thuê bao", "cards":"Quản lý thẻ xe", "fees":"Quản lý biểu phí", "lanes":"Cấu hình làn xe", "vehicle_types":"Cấu hình loại xe", "alerts":"Cảnh báo", "accounts":"Tài khoản & phân quyền", "self.settings":"Cài đặt hệ thống", "hardware":"Kết nối & Cài đặt thiết bị thật"}[key])
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
                try: rows = asyncio.run(loader(self.settings))
                except Exception as exc: show_toast(self, str(exc, "error")); return
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

