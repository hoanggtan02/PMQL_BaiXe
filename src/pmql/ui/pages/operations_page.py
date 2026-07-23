from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class OperationsPageMixin:
    def operations_page(self) -> QWidget:
            page, box = self.page(); box.setContentsMargins(12, 12, 12, 12); box.setSpacing(12)
            
            # --- Toolbar ---
            toolbar = QHBoxLayout()
            lane_filter = QComboBox(); lane_filter.addItem("— Tất cả làn —")
            try:
                for ln in asyncio.run(_lanes(self.settings)): lane_filter.addItem(ln.name)
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
            try: lanes = asyncio.run(_lanes(self.settings))
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
                lanes = asyncio.run(_lanes(self.settings))
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
                    self.shift_id = asyncio.run(_open_shift(self.settings, getattr(self.user, "user_id"), lane_id=lane_id, opening_cash=start_cash, note=note_txt))
                except Exception as exc: show_toast(dialog, str(exc), "error"); return
                self.shift_status_badge.setText("Ca đang hoạt động"); self.shift_status_badge.setStyleSheet("background: #dcfce7; color: #166534; border: 1px solid #bbf7d0;")
                self.shift_button.setText("✓ Ca đang hoạt động")
                self.refresh_live(); self.reload_page("shifts"); dialog.accept()
            save.clicked.connect(do_open); dialog.exec()

    def record_entry(self, lane_id: str) -> None:
            if not self.shift_id: show_toast(self, "Hãy mở ca làm việc trước.", "error"); return
            plate, ok = QInputDialog.getText(self, "Xe vào", "Biển số xe:");
            if not ok or not plate.strip(): return
            try:
                vehicle_types = asyncio.run(_vehicle_types(self.settings))
            except Exception as exc:
                show_toast(self, str(exc), "error"); return
            labels = [item.display_name for item in vehicle_types]
            vehicle, ok = QInputDialog.getItem(self, "Loại xe", "Chọn loại xe:", labels, 0, False)
            if not ok: return
            vehicle_code = next((item.code for item in vehicle_types if item.display_name == vehicle), None)
            try: asyncio.run(_entry(self.settings, lane_id, plate.strip(), vehicle_code, self.shift_id)); self.refresh_live()
            except Exception as exc: show_toast(self, str(exc), "error")

    def record_exit(self, lane_id: str) -> None:
            plate, ok = QInputDialog.getText(self, "Xe ra", "Biển số xe:");
            if not ok or not plate.strip(): return
            try: fee, minutes = asyncio.run(_exit(self.settings, lane_id, plate.strip())); show_toast(self, f"Phí: {fee:,} VND\nThời gian: {minutes} phút", "success"); self.refresh_live()
            except Exception as exc: show_toast(self, str(exc), "error")

    def refresh_live(self) -> None:
            try: stats = asyncio.run(_stats(self.settings, self.shift_id))
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

    def fill_vehicle_combo(self, combo: QComboBox) -> None:
            """Use configured vehicle types everywhere; display names stay user-friendly."""
            combo.clear()
            try:
                for item in asyncio.run(_vehicle_types(self.settings)):
                    combo.addItem(item.display_name, item.code)
            except Exception as exc:
                show_toast(self, str(exc), "error")

