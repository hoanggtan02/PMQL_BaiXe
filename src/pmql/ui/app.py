"""Polished PySide6 desktop adapter for the local parking application."""

from __future__ import annotations

import asyncio

from pmql.application.use_cases.auth.login_use_case import LoginInput, LoginUseCase
from pmql.config import Settings
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.repositories import SQLiteUserRepository
from pmql.infrastructure.security.jwt_token_service import JwtTokenService
from pmql.infrastructure.security.password_hasher import PBKDF2PasswordHasher


APP_STYLE = """
QWidget { font-family: 'Segoe UI', Arial; color: #1d2939; font-size: 13px; }
QLineEdit { background: #f6f8fb; border: 1px solid #e4e7ec; border-radius: 8px; padding: 11px 12px; }
QLineEdit:focus { background: white; border: 2px solid #f79009; }
QPushButton { border: 0; border-radius: 8px; padding: 10px 14px; font-weight: 600; }
QPushButton#loginButton { color: white; background: #f27816; font-size: 14px; }
QPushButton#loginButton:hover { background: #dd6510; }
QPushButton#navButton { color: #b8bdc9; background: transparent; text-align: left; padding: 10px 14px; }
QPushButton#navButton:hover, QPushButton#navButton[active='true'] { color: white; background: #35313a; }
QPushButton#actionGreen { background: #12b76a; color: white; }
QPushButton#actionRed { background: #f04438; color: white; }
QPushButton#actionOrange { background: #f79009; color: white; }
QFrame#metric { background: white; border: 1px solid #eaecf0; border-radius: 10px; }
QFrame#lane { background: white; border: 1px solid #eaecf0; border-radius: 12px; }
QLabel#muted { color: #98a2b3; }
QLabel#badge { background: #ecfdf3; color: #027a48; border-radius: 9px; padding: 3px 8px; font-size: 11px; font-weight: 700; }
QLabel#camera { background: #1d1b20; color: #75e345; border-radius: 8px; font-weight: 600; }
"""


def _label(text: str, *, object_name: str | None = None, bold: bool = False):
    from PySide6.QtWidgets import QLabel

    label = QLabel(text)
    if object_name:
        label.setObjectName(object_name)
    if bold:
        font = label.font()
        font.setBold(True)
        label.setFont(font)
    return label


def launch(settings: Settings) -> int:
    """Start the desktop UI. PySide6 remains an optional install."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import (
            QApplication, QFrame, QFormLayout, QGridLayout, QHBoxLayout,
            QLabel, QLineEdit, QMainWindow, QPushButton, QVBoxLayout, QWidget,
        )
    except ImportError as exc:
        raise RuntimeError('PySide6 is not installed. Run: pip install -e ".[gui]"') from exc

    class LoginWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("PMQL Bãi Xe – Đăng nhập")
            self.setMinimumSize(1040, 650)
            self.setStyleSheet(APP_STYLE)

            root = QHBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            hero = QFrame()
            hero.setStyleSheet("""
                QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #26232a, stop:.52 #253452, stop:1 #0058a9); }
                QLabel { color: white; }
            """)
            hero_layout = QVBoxLayout(hero)
            hero_layout.setContentsMargins(76, 72, 76, 72)
            hero_layout.addStretch(2)
            logo = _label("▣", bold=True)
            logo.setStyleSheet("background: #ff8a18; border-radius: 14px; padding: 10px; font-size: 27px;")
            logo.setFixedSize(58, 58)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hero_layout.addWidget(logo)
            title = _label("PMQL Bãi Xe", bold=True)
            title.setStyleSheet("font-size: 28px; margin-top: 16px;")
            hero_layout.addWidget(title)
            subtitle = _label("Hệ thống quản lý bãi xe thông minh tích hợp AI")
            subtitle.setStyleSheet("color: #d0d5dd; font-size: 14px; margin-top: 3px; margin-bottom: 30px;")
            hero_layout.addWidget(subtitle)
            for icon, text, color in (
                ("▣", "Nhận dạng biển số xe tự động (ANPR) bằng AI", "#f79009"),
                ("▥", "Kiểm soát ra vào bằng thẻ RFID & vân tay", "#2e90fa"),
                ("⚑", "Điều khiển barrier tự động thời gian thực", "#32d583"),
                ("⌁", "Báo cáo doanh thu & thống kê thông minh", "#7a5af8"),
                ("▦", "Thanh toán QR, ví điện tử đa ngân hàng", "#fdb022"),
            ):
                row = QHBoxLayout()
                badge = _label(icon, bold=True)
                badge.setStyleSheet(f"background: {color}; color: white; border-radius: 7px; padding: 5px;")
                badge.setFixedSize(30, 30)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                row.addWidget(badge)
                row.addWidget(_label(text))
                row.addStretch()
                hero_layout.addLayout(row)
                hero_layout.addSpacing(9)
            hero_layout.addStretch(2)

            form_panel = QFrame()
            form_panel.setStyleSheet("background: #ffffff;")
            form_layout = QVBoxLayout(form_panel)
            form_layout.setContentsMargins(54, 72, 54, 55)
            form_layout.addStretch()
            heading = _label("Chào mừng trở lại", bold=True)
            heading.setStyleSheet("font-size: 24px;")
            form_layout.addWidget(heading)
            subheading = _label("Đăng nhập để quản lý bãi xe của bạn", object_name="muted")
            form_layout.addWidget(subheading)
            form_layout.addSpacing(30)
            self._username = QLineEdit()
            self._username.setPlaceholderText("Nhập tên đăng nhập")
            self._username.setText("admin")
            self._password = QLineEdit()
            self._password.setPlaceholderText("Nhập mật khẩu")
            self._password.setEchoMode(QLineEdit.EchoMode.Password)
            form = QFormLayout()
            form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            form.setVerticalSpacing(8)
            form.addRow(_label("Tên đăng nhập", bold=True), self._username)
            form.addRow(_label("Mật khẩu", bold=True), self._password)
            form_layout.addLayout(form)
            form_layout.addSpacing(18)
            login = QPushButton("↪  Đăng nhập")
            login.setObjectName("loginButton")
            login.clicked.connect(self._login)
            self._password.returnPressed.connect(self._login)
            form_layout.addWidget(login)
            self._message = _label("")
            self._message.setStyleSheet("color: #d92d20; margin-top: 8px;")
            form_layout.addWidget(self._message)
            form_layout.addSpacing(22)
            hint = _label("TÀI KHOẢN THỬ NGHIỆM", object_name="muted", bold=True)
            hint.setStyleSheet("color: #98a2b3; font-size: 10px;")
            form_layout.addWidget(hint)
            form_layout.addWidget(_label("admin / MatKhau123!", object_name="muted"))
            form_layout.addStretch()
            form_layout.addWidget(_label("© 2026 PMQL · Hệ Thống Quản Lý Bãi Xe v2.0", object_name="muted"))
            root.addWidget(hero, 7)
            root.addWidget(form_panel, 4)

        def _login(self) -> None:
            try:
                result = asyncio.run(_authenticate(settings, self._username.text(), self._password.text()))
            except Exception:
                self._message.setText("Không thể đăng nhập. Kiểm tra tài khoản hoặc mật khẩu.")
                return
            self._dashboard = Dashboard(result)
            self._dashboard.show()
            self.close()

    class Dashboard(QMainWindow):
        def __init__(self, result: object) -> None:
            super().__init__()
            self.setWindowTitle("PMQL Bãi Xe – Vận hành làn xe")
            self.setMinimumSize(1250, 760)
            self.setStyleSheet(APP_STYLE)
            name, role = getattr(result, "full_name"), getattr(result, "role")
            page = QWidget()
            root = QHBoxLayout(page)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)
            root.addWidget(self._sidebar(role), 0)
            root.addWidget(self._content(name, role), 1)
            self.setCentralWidget(page)

        def _sidebar(self, role: str) -> QWidget:
            panel = QFrame()
            panel.setFixedWidth(225)
            panel.setStyleSheet("QFrame { background: #211f25; } QLabel { color: white; }")
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(12, 20, 12, 18)
            brand = _label("▣  PMQL BÃI XE", bold=True)
            brand.setStyleSheet("font-size: 15px; color: white; padding: 8px 10px;")
            layout.addWidget(brand)
            layout.addSpacing(18)
            for index, text in enumerate(("◉  Tổng quan", "⚑  Vận hành làn", "◌  Phiên gửi xe", "▲  Cảnh báo", "↻  Ca làm việc")):
                button = QPushButton(text)
                button.setObjectName("navButton")
                button.setProperty("active", index == 1)
                layout.addWidget(button)
            layout.addSpacing(12)
            layout.addWidget(_label("QUẢN LÝ", object_name="muted", bold=True))
            for text in ("▣  Thuê bao", "▤  Thẻ xe", "◆  Biểu phí"):
                button = QPushButton(text)
                button.setObjectName("navButton")
                layout.addWidget(button)
            if role in {"SUPERVISOR", "ADMIN"}:
                layout.addWidget(_label("PHÂN TÍCH", object_name="muted", bold=True))
                button = QPushButton("▰  Báo cáo")
                button.setObjectName("navButton")
                layout.addWidget(button)
            layout.addStretch()
            layout.addWidget(_label("Đang đăng nhập", object_name="muted"))
            layout.addWidget(_label(role.replace("_", " "), object_name="badge", bold=True))
            return panel

        def _content(self, name: str, role: str) -> QWidget:
            page = QWidget()
            page.setStyleSheet("background: #f8fafc;")
            layout = QVBoxLayout(page)
            layout.setContentsMargins(26, 18, 26, 24)
            top = QHBoxLayout()
            heading = _label("☰    ⚑  Vận hành làn xe", bold=True)
            heading.setStyleSheet("font-size: 17px;")
            top.addWidget(heading)
            top.addStretch()
            online = _label("● Kết nối", object_name="badge", bold=True)
            top.addWidget(online)
            top.addSpacing(15)
            top.addWidget(_label(f"{name} · {role}", object_name="muted"))
            layout.addLayout(top)
            layout.addSpacing(18)
            controls = QHBoxLayout()
            controls.addWidget(_label("— Tất cả làn —", bold=True))
            controls.addSpacing(20)
            controls.addWidget(_label("Chưa mở ca", object_name="badge"))
            controls.addStretch()
            open_shift = QPushButton("▶  Mở ca")
            open_shift.setObjectName("actionGreen")
            controls.addWidget(open_shift)
            layout.addLayout(controls)
            metrics = QFrame()
            metrics.setObjectName("metric")
            metrics.setStyleSheet("QFrame#metric { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #182a64, stop:1 #625682); }")
            metric_layout = QHBoxLayout(metrics)
            for value, caption, color in (("0 xe", "XE TRONG BÃI", "#ffffff"), ("0 đ", "DOANH THU HÔM NAY", "#6ce9a6"), ("0 đ", "DOANH THU CA NÀY", "#f9d36a"), ("0 lượt", "LƯỢT XE HÔM NAY", "#8bd5ff")):
                block = QVBoxLayout()
                v = _label(value, bold=True)
                v.setStyleSheet(f"color: {color}; font-size: 18px;")
                block.addWidget(v)
                c = _label(caption)
                c.setStyleSheet("color: #cbd5e1; font-size: 10px;")
                block.addWidget(c)
                metric_layout.addLayout(block)
                metric_layout.addStretch()
            layout.addWidget(metrics)
            grid = QGridLayout()
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(14)
            for i, lane in enumerate(("Làn vào 1", "Làn vào 2", "Làn ra 1", "Làn ra 2")):
                grid.addWidget(self._lane_card(lane, "VÀO" if "vào" in lane else "RA"), i // 3, i % 3)
            layout.addLayout(grid)
            layout.addStretch()
            return page

        def _lane_card(self, lane: str, direction: str) -> QWidget:
            card = QFrame()
            card.setObjectName("lane")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 12, 14, 14)
            header = QHBoxLayout()
            header.addWidget(_label(lane, bold=True))
            status = _label(direction, object_name="badge", bold=True)
            header.addWidget(status)
            header.addStretch()
            header.addWidget(_label("0 xe", object_name="badge"))
            layout.addLayout(header)
            state = _label("●  Chờ xe", bold=True)
            state.setStyleSheet("color: #475467; margin-top: 4px;")
            layout.addWidget(state)
            plate = _label("—")
            plate.setAlignment(Qt.AlignmentFlag.AlignCenter)
            plate.setStyleSheet("background: #fff9df; border: 2px solid #f9d36a; border-radius: 7px; font-size: 24px; padding: 8px;")
            layout.addWidget(plate)
            camera = _label("▣\nCamera đang chờ...", object_name="camera", bold=True)
            camera.setAlignment(Qt.AlignmentFlag.AlignCenter)
            camera.setMinimumHeight(83)
            layout.addWidget(camera)
            action = QHBoxLayout()
            for text, name in (("↪  Vào", "actionGreen"), ("↩  Ra", "actionRed"), ("▣  Chụp", "actionOrange")):
                button = QPushButton(text)
                button.setObjectName(name)
                action.addWidget(button)
            layout.addLayout(action)
            return card

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = LoginWindow()
    window.show()
    return app.exec()


async def _authenticate(settings: Settings, username: str, password: str):
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            return await LoginUseCase(
                SQLiteUserRepository(session),
                PBKDF2PasswordHasher(),
                JwtTokenService(settings.secret_key, settings.access_token_expire_minutes),
            ).execute(LoginInput(username=username, password=password))
    finally:
        await db.dispose()
