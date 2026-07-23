from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QLineEdit, QPushButton
from PySide6.QtCore import Qt
from pmql.ui.components import LIGHT_THEME as THEME, label
from pmql.ui.db_helpers import _authenticate
import asyncio

class Login(QWidget):
    def __init__(self, settings, MainWindowClass) -> None:
        super().__init__()
        self.settings = settings
        self.MainWindowClass = MainWindowClass
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
        try: result = asyncio.run(_authenticate(self.settings, self.username.text(), self.password.text()))
        except Exception: self.notice.setText("Không thể đăng nhập. Kiểm tra lại tài khoản hoặc mật khẩu."); return
        self.window = self.MainWindowClass(result, self.settings); self.window.showMaximized(); self.close()

