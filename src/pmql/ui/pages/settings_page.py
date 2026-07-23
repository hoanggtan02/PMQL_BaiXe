from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class SettingsPageMixin:
    def settings_page(self) -> QWidget:
            page, box = self.page(); h = label("Cài đặt hệ thống", bold=True); h.setStyleSheet("font-size:24px;"); box.addWidget(h)
            
            try:
                import asyncio
                sys_settings = asyncio.run(_load_sys_settings(self.settings))
            except Exception as e:
                print("Error loading sys self.settings:", e)
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
                asyncio.run(_save_sys_settings(self.settings, data))
                show_toast(self, "Đã lưu cài đặt hệ thống!", "success")
                
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
                    db = Database(self.settings.local_database_url)
                    try:
                        async with db.session() as session:
                            s_repo = SQLiteSessionRepository(session)
                            all_sessions = await s_repo.list_recent(self.settings.branch_id, 5000)
                            
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

