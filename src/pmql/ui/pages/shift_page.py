from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class ShiftPageMixin:
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
                try: stats = asyncio.run(_stats(self.settings, self.shift_id))
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
            try: rows = asyncio.run(_shift_rows(self.settings))
            except Exception: rows = []
            table.setRowCount(len(rows))
            for r, values in enumerate(rows):
                for c, value in enumerate(values): table.setItem(r, c, QTableWidgetItem(str(value)))
            
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
            try: shifts = asyncio.run(_shift_entities(self.settings))
            except Exception: return
            
            self.shift_table.setRowCount(len(shifts))
            for r, s in enumerate(shifts):
                row_data = [
                    s.id[:8], s.operator_id, s.note or "—", s.lane_id or "Tất cả",
                    f"{s.opening_cash:,} đ", f"{s.total_revenue:,} đ",
                    s.start_time.strftime("%d/%m %H:%M"), s.end_time.strftime("%d/%m %H:%M") if s.end_time else "—", s.status
                ]
                for c, value in enumerate(row_data): self.shift_table.setItem(r, c, QTableWidgetItem(str(value)))
                actions = QWidget(); actions.setMinimumHeight(38); actions_row = QHBoxLayout(actions); actions_row.setContentsMargins(4, 2, 4, 2)
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
                for ln in asyncio.run(_lanes(self.settings)): lane_combo.addItem(ln.name, ln.id)
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
                    asyncio.run(_open_shift(self.settings, self.user.user_id, lane_combo.currentData(), type_combo.currentText(), cash_val))
                    self.load_shifts(); dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
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
                    asyncio.run(_close_shift(self.settings, s.operator_id, cash_val, note_txt))
                    self.load_shifts(); dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save.clicked.connect(save_shift); dialog.exec()

    def edit_shift(self, shift) -> None:
            dialog, content, footer = modal_shell(self, "Sửa ca làm việc", 560); form = QFormLayout(); content.addLayout(form)
            operator_id, start_time = QComboBox(), QLineEdit()
            try:
                for u in asyncio.run(_users(self.settings)):
                    operator_id.addItem(f"{u.full_name} ({u.username})", u.id)
                    if u.id == shift.operator_id: operator_id.setCurrentIndex(operator_id.count() - 1)
            except Exception: pass
            start_time.setText(shift.start_time.strftime("%Y-%m-%d %H:%M:%S"))
            form.addRow("Tài khoản NV *", operator_id); form.addRow("Bắt đầu * (YYYY-MM-DD HH:MM:SS)", start_time)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_shift() -> None:
                try: 
                    st = datetime.strptime(start_time.text().strip(), "%Y-%m-%d %H:%M:%S")
                    inp = ShiftInput(self.settings.branch_id, operator_id.currentData() or shift.operator_id, st, shift.end_time, shift.total_sessions, shift.total_revenue, shift.status)
                    asyncio.run(_update_shift(self.settings, shift.id, inp)); self.load_shifts(); dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save.clicked.connect(save_shift); dialog.exec()

    def delete_shift(self, shift) -> None:
            if QMessageBox.question(self, "Xóa ca", f"Xóa vĩnh viễn ca làm việc này?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_shift(self.settings, shift.id)); self.load_shifts()
            except Exception as exc: show_toast(self, str(exc), "error")

    def close_shift(self) -> None:
            if not self.shift_id: return
            dialog, content, footer = modal_shell(self, "Tính toán & Đóng ca", 600)
            
            grid = QGridLayout()
            grid.addWidget(label("Tổng tiền mặt thực tế", "muted"), 0, 0)
            actual_cash = QLineEdit(); actual_cash.setPlaceholderText("0 đ"); grid.addWidget(actual_cash, 1, 0)
            
            grid.addWidget(label("Ghi chú đóng ca", "muted"), 2, 0)
            note = QLineEdit(); note.setPlaceholderText("Ghi chú (bàn giao ca, chênh lệch...)"); grid.addWidget(note, 3, 0)
            content.addLayout(grid)
            
            try: stats = asyncio.run(_stats(self.settings, self.shift_id))
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
                    asyncio.run(_close_shift(self.settings, getattr(self.user, "user_id"), actual, note.text()))
                except Exception as exc: show_toast(dialog, str(exc), "error"); return
                self.shift_id = None
                self.shift_status_badge.setText("Chưa mở ca"); self.shift_status_badge.setStyleSheet("background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1;")
                self.shift_button.setText("▶ Mở ca")
                self.reload_page("shifts")
                dialog.accept()
            save.clicked.connect(do_close); dialog.exec()

