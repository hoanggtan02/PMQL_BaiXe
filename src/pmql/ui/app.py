"""Minimal, real PySide6 login flow for the local parking application."""

from __future__ import annotations

import asyncio

from pmql.application.use_cases.auth.login_use_case import LoginInput, LoginUseCase
from pmql.config import Settings
from pmql.infrastructure.persistence.sqlite.database import Database
from pmql.infrastructure.persistence.sqlite.repositories import SQLiteUserRepository
from pmql.infrastructure.security.jwt_token_service import JwtTokenService
from pmql.infrastructure.security.password_hasher import PBKDF2PasswordHasher


def launch(settings: Settings) -> int:
    """Start the desktop UI. PySide6 remains an optional install."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication, QFormLayout, QLabel, QLineEdit, QMainWindow,
            QPushButton, QVBoxLayout, QWidget,
        )
    except ImportError as exc:
        raise RuntimeError('PySide6 is not installed. Run: pip install -e ".[gui]"') from exc

    class LoginWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("PMQL Bãi Xe – Đăng nhập")
            self.setMinimumWidth(360)
            self._username = QLineEdit()
            self._password = QLineEdit()
            self._password.setEchoMode(QLineEdit.EchoMode.Password)
            self._message = QLabel()
            self._message.setStyleSheet("color: #b00020")
            login = QPushButton("Đăng nhập")
            login.clicked.connect(self._login)
            form = QFormLayout()
            form.addRow("Tên đăng nhập", self._username)
            form.addRow("Mật khẩu", self._password)
            layout = QVBoxLayout(self)
            title = QLabel("PMQL Bãi Xe")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title)
            layout.addLayout(form)
            layout.addWidget(self._message)
            layout.addWidget(login)

        def _login(self) -> None:
            try:
                result = asyncio.run(_authenticate(settings, self._username.text(), self._password.text()))
            except Exception:  # Show a generic message; never expose password/token details.
                self._message.setText("Không thể đăng nhập. Kiểm tra tài khoản hoặc mật khẩu.")
                return
            self._dashboard = Dashboard(result)
            self._dashboard.show()
            self.close()

    class Dashboard(QMainWindow):
        def __init__(self, result: object) -> None:
            super().__init__()
            self.setWindowTitle("PMQL Bãi Xe")
            self.setMinimumSize(560, 300)
            # LoginOutput is deliberately kept private to the UI adapter.
            name = getattr(result, "full_name")
            role = getattr(result, "role")
            expires = getattr(result, "token_expires_at")
            body = QWidget()
            layout = QVBoxLayout(body)
            layout.addWidget(QLabel(f"Đang đăng nhập: {name} ({role})"))
            layout.addWidget(QLabel(f"Phiên đăng nhập hết hạn: {expires.isoformat(timespec='minutes') if expires else '-'}"))
            layout.addWidget(QPushButton("Vào xe / Ra xe"))
            if role in {"SUPERVISOR", "ADMIN"}:
                layout.addWidget(QPushButton("Quản lý thuê bao"))
                layout.addWidget(QPushButton("Xác nhận cảnh báo"))
            if role == "ADMIN":
                layout.addWidget(QPushButton("Quản lý tài khoản"))
            layout.addStretch()
            self.setCentralWidget(body)

    app = QApplication.instance() or QApplication([])
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
