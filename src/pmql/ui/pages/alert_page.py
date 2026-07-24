from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import datetime
import json

class AlertPageMixin:
    def alert_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Header
        header = QHBoxLayout()
        header.addWidget(label("Trung tâm cảnh báo", bold=True, style="font-size: 24px;"))
        header.addStretch()
        layout.addLayout(header)
        
        # 2. Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self.lbl_alert_today = label("0", bold=True, style="font-size: 30px;")
        self.lbl_alert_open = label("0", bold=True, style="font-size: 30px; color: #ef4444;")
        self.lbl_alert_critical = label("0", bold=True, style="font-size: 30px; color: #ef4444;")
        self.lbl_alert_warning = label("0", bold=True, style="font-size: 30px; color: #f59e0b;")

        def _make_stat_card(title, lbl_val, border_color=""):
            c = QFrame()
            c.setObjectName("statCard")
            style = "QFrame#statCard { background: white; border-radius: 8px; "
            if border_color:
                style += f"border: 1px solid {border_color}; "
            style += "}"
            c.setStyleSheet(style)
            cl = QVBoxLayout(c)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_title = label(title, style="color: #64748b; font-size: 13px;")
            lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(lbl_title)
            cl.addWidget(lbl_val)
            return c
            
        stats_layout.addWidget(_make_stat_card("Hôm nay", self.lbl_alert_today))
        stats_layout.addWidget(_make_stat_card("Đang mở", self.lbl_alert_open, "#ef4444"))
        stats_layout.addWidget(_make_stat_card("CRITICAL", self.lbl_alert_critical))
        stats_layout.addWidget(_make_stat_card("WARNING", self.lbl_alert_warning, "#f59e0b"))
        
        layout.addLayout(stats_layout)

        # 3. Filters row
        filters = QHBoxLayout()
        filters.setSpacing(12)
        
        self.cbo_alert_status = QComboBox()
        self.cbo_alert_status.addItems(["", "OPEN", "HANDLED"])
        self.cbo_alert_status.setItemText(0, "Tất cả trạng thái")
        self.cbo_alert_status.setItemText(1, "Đang mở")
        self.cbo_alert_status.setItemText(2, "Đã xử lý")
        self.cbo_alert_status.setMinimumHeight(32)
        self.cbo_alert_status.setMinimumWidth(140)
        self.cbo_alert_status.currentIndexChanged.connect(self.load_alerts)
        
        self.cbo_alert_severity = QComboBox()
        self.cbo_alert_severity.addItems(["", "CRITICAL", "WARNING", "INFO"])
        self.cbo_alert_severity.setItemText(0, "Mọi mức độ")
        self.cbo_alert_severity.setMinimumHeight(32)
        self.cbo_alert_severity.setMinimumWidth(130)
        self.cbo_alert_severity.currentIndexChanged.connect(self.load_alerts)

        btn_refresh = icon_btn("fa5s.sync", "Làm mới", _BTN_PLAIN_STYLE)
        btn_refresh.clicked.connect(self.load_alerts)
        
        btn_handle_all = icon_btn("fa5s.check-double", "Xử lý tất cả đang mở", _BTN_EDIT_STYLE)
        btn_handle_all.setStyleSheet(btn_handle_all.styleSheet().replace("#3b82f6", "#10b981").replace("#2563eb", "#059669")) # Make it green
        btn_handle_all.clicked.connect(self.handle_all_open_alerts)
        
        filters.addWidget(self.cbo_alert_status)
        filters.addWidget(self.cbo_alert_severity)
        filters.addWidget(btn_refresh)
        filters.addStretch()
        filters.addWidget(btn_handle_all)
        layout.addLayout(filters)

        # 4. Scroll Area for Alerts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.alerts_container = QWidget()
        self.alerts_container.setStyleSheet("background: transparent;")
        self.alerts_layout = QVBoxLayout(self.alerts_container)
        self.alerts_layout.setContentsMargins(0, 0, 0, 0)
        self.alerts_layout.setSpacing(10)
        self.alerts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.alerts_container)
        layout.addWidget(scroll)

        # Initial load delayed slightly to ensure UI is ready
        QTimer.singleShot(100, self.load_alerts)

        return page

    def load_alerts(self):
        try:
            stats = asyncio.run(_alert_stats(self.settings))
            self.lbl_alert_today.setText(str(stats["total_today"]))
            self.lbl_alert_open.setText(str(stats["open"]))
            self.lbl_alert_critical.setText(str(stats["critical"]))
            self.lbl_alert_warning.setText(str(stats["warning"]))
            
            status = ["", "OPEN", "HANDLED"][self.cbo_alert_status.currentIndex()]
            severity = ["", "CRITICAL", "WARNING", "INFO"][self.cbo_alert_severity.currentIndex()]
            
            alerts = asyncio.run(_alert_list(self.settings, status, severity))
            
            # Clear layout
            while self.alerts_layout.count():
                item = self.alerts_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
                
            if not alerts:
                empty = label("Không có cảnh báo", style="color: #64748b; font-size: 16px;")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.alerts_layout.addWidget(empty)
                return
                
            alert_labels = {
                'PLATE_MISMATCH_ENTRY':'🚗 Biển số vào không khớp',
                'PLATE_MISMATCH_EXIT' :'🚗 Biển số ra không khớp',
                'CARD_EXPIRED'        :'📅 Thẻ hết hạn',
                'CARD_INVALID'        :'🚫 Thẻ không hợp lệ',
                'DOUBLE_ENTRY'        :'⚠️ Đăng ký 2 lần',
                'NO_CARD_VISITOR'     :'🎫 Xe chưa có thẻ',
                'TAILGATING'          :'🏃 Xe theo đuôi',
                'DEVICE_OFFLINE'      :'📡 Thiết bị offline',
                'STAFF_OVERRIDE'      :'👤 Override bởi NV',
                'CARD_NOT_FOUND'      :'❓ Không tìm thấy thẻ',
                'NO_OPEN_SESSION'     :'❓ Không có phiên mở'
            }
            
            sev_colors = {'CRITICAL': '#ef4444', 'WARNING': '#f59e0b', 'INFO': '#3b82f6'}
            
            for a in alerts:
                color = sev_colors.get(a.severity, '#94a3b8')
                
                card = QFrame()
                card.setStyleSheet(f"QFrame {{ background: white; border-radius: 8px; border-left: 4px solid {color}; }}")
                row = QHBoxLayout(card)
                row.setContentsMargins(16, 12, 16, 12)
                row.setSpacing(16)
                
                # Badge
                badge = label(a.severity, bold=True, style=f"color: white; background: {color}; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
                badge.setAlignment(Qt.AlignmentFlag.AlignTop)
                
                badge_layout = QVBoxLayout()
                badge_layout.addWidget(badge)
                badge_layout.addStretch()
                row.addLayout(badge_layout)
                
                # Info
                info_col = QVBoxLayout()
                title_text = alert_labels.get(a.alert_type, a.alert_type)
                info_col.addWidget(label(title_text, bold=True, style="font-size: 14px;"))
                
                time_str = a.created_at.strftime("%H:%M:%S %d/%m/%Y")
                
                try:
                    payload = json.loads(a.payload or "{}")
                except:
                    payload = {}
                    
                lane_name_text = ""
                if payload.get("lane_name"):
                    lane_name_text = f"Làn: <b>{payload['lane_name']}</b> | "
                info_col.addWidget(label(f"{lane_name_text}{time_str}", style="color: #64748b; font-size: 12px;"))
                    
                if payload.get("message"):
                    info_col.addWidget(label(payload["message"], style="font-size: 13px; margin-top: 4px;"))
                    
                if payload.get("entry_plate") or payload.get("exit_plate"):
                    plates = QHBoxLayout()
                    if payload.get("entry_plate"):
                        lbl = label(f"Vào: {payload['entry_plate']}", style="background: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-size: 12px;")
                        plates.addWidget(lbl)
                    if payload.get("exit_plate"):
                        lbl = label(f"Ra: {payload['exit_plate']}", style="background: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-size: 12px;")
                        plates.addWidget(lbl)
                    plates.addStretch()
                    
                    plates_widget = QWidget()
                    plates_widget.setLayout(plates)
                    plates.setContentsMargins(0, 4, 0, 0)
                    info_col.addWidget(plates_widget)
                    
                if a.is_acknowledged:
                    ack_time = a.acknowledged_at.strftime("%H:%M:%S %d/%m/%Y") if a.acknowledged_at else ""
                    info_col.addWidget(label(f"✓ Xử lý bởi {a.acknowledged_by or 'admin'} - {ack_time}: {a.handle_note}", style="color: #10b981; font-size: 12px; margin-top: 4px;"))
                    
                row.addLayout(info_col, 1)
                
                # Actions
                acts_col = QVBoxLayout()
                acts_col.setAlignment(Qt.AlignmentFlag.AlignTop)
                acts_col.setSpacing(6)
                if not a.is_acknowledged:
                    btn_handle = icon_btn("fa5s.check", "Xử lý", _BTN_EDIT_STYLE)
                    btn_handle.setStyleSheet(btn_handle.styleSheet().replace("#3b82f6", "#10b981").replace("#2563eb", "#059669"))
                    btn_handle.clicked.connect(lambda _, aid=a.id: self.handle_alert_prompt(aid))
                    
                    btn_open = icon_btn("fa5s.door-open", "Mở", _BTN_DEL_STYLE)
                    lane_id = payload.get("lane_id", "")
                    btn_open.clicked.connect(lambda _, lid=lane_id: self.open_barrier_alert(lid))
                    
                    btn_dismiss = icon_btn("", "Bỏ qua", _BTN_PLAIN_STYLE)
                    btn_dismiss.clicked.connect(lambda _, aid=a.id: self.dismiss_alert(aid))
                    
                    acts_col.addWidget(btn_handle)
                    acts_col.addWidget(btn_open)
                    acts_col.addWidget(btn_dismiss)
                else:
                    status_lbl = label("Đã xử lý", bold=True, style="color: white; background: #10b981; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
                    acts_col.addWidget(status_lbl)
                
                row.addLayout(acts_col)
                self.alerts_layout.addWidget(card)
                
        except Exception as e:
            print("load_alerts err:", e)
            
    def handle_alert_prompt(self, alert_id):
        dialog, content, footer = modal_shell(self, "Xử lý cảnh báo", 400)
        note_inp = QLineEdit("Đã kiểm tra, hợp lệ")
        content.addWidget(label("Ghi chú xử lý:"))
        content.addWidget(note_inp)
        
        btn_cancel = icon_btn("", "Hủy", _BTN_PLAIN_STYLE)
        btn_save = icon_btn("fa5s.check", "Lưu", _BTN_EDIT_STYLE)
        btn_save.setStyleSheet(btn_save.styleSheet().replace("#3b82f6", "#10b981").replace("#2563eb", "#059669"))
        footer.addWidget(btn_cancel)
        footer.addWidget(btn_save)
        
        btn_cancel.clicked.connect(dialog.reject)
        
        def _save():
            try:
                username = getattr(self, "session_username", "admin")
                asyncio.run(_handle_alert(self.settings, alert_id, note_inp.text().strip(), username))
                show_toast(self, "Đã xử lý cảnh báo", "success")
                dialog.accept()
                self.load_alerts()
            except Exception as e:
                show_toast(self, f"Lỗi: {e}", "danger")
                
        btn_save.clicked.connect(_save)
        dialog.exec()

    def dismiss_alert(self, alert_id):
        try:
            asyncio.run(_dismiss_alert(self.settings, alert_id))
            self.load_alerts()
        except Exception as e:
            show_toast(self, f"Lỗi: {e}", "danger")
            
    def open_barrier_alert(self, lane_id):
        if not lane_id:
            show_toast(self, "Không tìm thấy làn xe", "danger")
            return
        try:
            asyncio.run(_open_barrier_alert(self.settings, lane_id))
            show_toast(self, "Barrier đã mở", "success")
        except Exception as e:
            show_toast(self, f"Lỗi: {e}", "danger")
            
    def handle_all_open_alerts(self):
        try:
            username = getattr(self, "session_username", "admin")
            asyncio.run(_handle_all_open_alerts(self.settings, username))
            show_toast(self, "Đã xử lý tất cả cảnh báo", "success")
            self.load_alerts()
        except Exception as e:
            show_toast(self, f"Lỗi: {e}", "danger")
