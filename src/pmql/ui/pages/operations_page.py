from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class OperationsPageMixin:
    def operations_page(self) -> QWidget:
        page, box = self.page(); box.setContentsMargins(16, 16, 16, 16); box.setSpacing(16)
        
        # --- Toolbar ---
        # --- Title Row ---
        title_bar = QHBoxLayout()
        title_bar.addWidget(label("Vận hành làn xe", style="font-size: 20px; font-weight: 800; color: #1e293b; margin-bottom: 4px;"))
        title_bar.addStretch()
        box.addLayout(title_bar)
        
        # Separator to match the screenshot layout
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;")
        box.addWidget(sep)
        box.addSpacing(4)
        
        # --- Controls Row ---
        controls_bar = QHBoxLayout()
        lane_filter = QComboBox(); lane_filter.addItem("— Tất cả làn —")
        try:
            for ln in asyncio.run(_lanes(self.settings)): lane_filter.addItem(ln.name)
        except Exception: pass
        lane_filter.setFixedWidth(200)
        lane_filter.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 8px; color: #334155; font-size: 13px; height: 28px;")
        controls_bar.addWidget(lane_filter)
        
        self.shift_status_badge = label("Chưa mở ca", "badge")
        self.shift_status_badge.setStyleSheet("background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; padding: 4px 12px; border-radius: 6px; font-weight: bold; font-size: 11px;")
        controls_bar.addWidget(self.shift_status_badge)
        controls_bar.addStretch()
        
        self.shift_button = QPushButton()
        self.shift_button.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_bar.addWidget(self.shift_button)
        self.setup_shift_ui()
        
        def do_filter(text):
            if not hasattr(self, 'lane_cards'): return
            for name, card in self.lane_cards:
                card.setVisible(False)
                grid.removeWidget(card)
            idx = 0
            for name, card in self.lane_cards:
                if "Tất cả làn" in text or text == name:
                    card.setVisible(True)
                    grid.addWidget(card, idx // 2, idx % 2)
                    idx += 1
        lane_filter.currentTextChanged.connect(do_filter)
        
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 6px; color: #64748b; font-weight: bold; font-size: 16px;")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_bar.addWidget(refresh_btn)
        box.addLayout(controls_bar)
        
        # --- Sub-Toolbar ---
        sub_toolbar = QHBoxLayout(); sub_toolbar.setSpacing(2)
        btn_operate = QPushButton("⚑ Vận hành"); btn_operate.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #4f46e5,stop:1 #7c3aed); color: white; border: none; border-top-left-radius: 6px; border-bottom-left-radius: 6px; padding: 6px 16px; font-weight: bold;")
        btn_operate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_camera = QPushButton("📷 Xem camera"); btn_camera.setStyleSheet("background: white; color: #475569; border: 1px solid #dee2e6; border-left: none; border-top-right-radius: 6px; border-bottom-right-radius: 6px; padding: 6px 16px; font-weight: bold;")
        btn_camera.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_camera.clicked.connect(lambda: show_toast(self, "Tính năng Xem camera đang được hoàn thiện", "info"))
        sub_toolbar.addWidget(btn_operate); sub_toolbar.addWidget(btn_camera)
        
        btn_finance = QPushButton("📊 Thu/Chi"); btn_finance.setStyleSheet("background: white; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 6px; padding: 6px 12px; font-weight: bold; margin-left: 8px;")
        btn_finance.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_finance.clicked.connect(lambda: show_toast(self, "Tính năng Thu/Chi đang được hoàn thiện", "info"))
        sub_toolbar.addWidget(btn_finance); sub_toolbar.addStretch()
        box.addLayout(sub_toolbar)
        
        # --- TCP RFID Hook ---
        def handle_rfid_scan(ip_addr: str, rfid_code: str):
            for i in range(grid.count()):
                item = grid.itemAt(i)
                if item and item.widget():
                    from PySide6.QtWidgets import QLineEdit
                    for le in item.widget().findChildren(QLineEdit):
                        if "UID" in le.placeholderText(): le.setText(rfid_code); return
        global_hw_signals.rfid_scanned.connect(handle_rfid_scan)

        # --- Financial Bar ---
        fin_bar = QFrame(); fin_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e1b4b, stop:1 #312e81); border-radius: 12px;")
        fin_lay = QHBoxLayout(fin_bar); fin_lay.setContentsMargins(16, 10, 16, 10); fin_lay.setSpacing(24)
        def fin_item(val, title, val_color="white"):
            w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.setSpacing(2)
            v = label(val); v.setStyleSheet(f"color: {val_color}; font-size: 16px; font-weight: 800;"); v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t = label(title); t.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.addWidget(v); l.addWidget(t); return w, v
        
        w1, self.lbl_in_lot = fin_item("—", "XE TRONG BÃI")
        w2, self.lbl_rev_today = fin_item("—", "DOANH THU HÔM NAY", "#4ade80")
        w3, self.lbl_rev_shift = fin_item("—", "DOANH THU CA NÀY", "#facc15")
        w4, self.lbl_count_today = fin_item("—", "LƯỢT XE HÔM NAY", "#67e8f9")
        w5, self.lbl_start_cash = fin_item("—", "TIỀN ĐẦU CA", "#fb923c")
        
        for idx, fw in enumerate([w1, w2, w3, w4]):
            fin_lay.addWidget(fw)
            if idx < 3: # add separator
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine); sep.setStyleSheet("border-left: 1px solid rgba(255,255,255,0.1);")
                fin_lay.addWidget(sep)
        fin_lay.addStretch(); fin_lay.addWidget(w5)
        box.addWidget(fin_bar)
        
        # --- Lane Grid ---
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        grid_w = QWidget(); grid = QGridLayout(grid_w); grid.setSpacing(16); grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(grid_w); box.addWidget(scroll, 1)
        self.lane_plate = []
        self.lane_b_arm = {}
        self.lane_status_lbl = {}
        self.lane_cards = []
        
        try: lanes = asyncio.run(_lanes(self.settings))
        except Exception: lanes = []
        if not lanes: grid.addWidget(label("Chưa có làn nào được thiết lập. Hãy tạo trong Cấu hình làn.", "muted")); return page
        
        for index, lane in enumerate(lanes):
            sk = "active" if lane.is_active else "inactive"
            card = QFrame(); card.setObjectName("lnPanel")
            # Mimic .lane-panel border styling
            card.setStyleSheet("QFrame#lnPanel { background: white; border: 2px solid #dee2e6; border-radius: 16px; }")
            cbox = QVBoxLayout(card); cbox.setContentsMargins(0, 0, 0, 0); cbox.setSpacing(0)
            
            # Header
            hdr = QWidget(); hdr.setStyleSheet("background: transparent; border-bottom: 1px solid #f1f5f9;")
            hl = QHBoxLayout(hdr); hl.setContentsMargins(16, 12, 16, 12); hl.setSpacing(8)
            hl.addWidget(label(lane.name, style="font-size: 14px; font-weight: 800; color: #1e293b;"))
            
            dir_bg, dir_fg, dir_txt = ("#dcfce7", "#166534", "VÀO ↗") if lane.direction == "IN" else ("#fee2e2", "#991b1b", "↙ RA") if lane.direction == "OUT" else ("#e0e7ff", "#3730a3", "↔ 2 CHIỀU")
            hl.addWidget(label(dir_txt, style=f"background: {dir_bg}; color: {dir_fg}; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold;"))
            hl.addWidget(label("⚫ CHỜ XE", style="background: #64748b; color: white; border-radius: 10px; padding: 2px 8px; font-size: 10px; font-weight: bold;"))
            hl.addStretch()
            hl.addWidget(label("0 xe", style="background: #e2e8f0; color: #475569; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;"))
            cbox.addWidget(hdr)
            
            # Body
            bdy = QWidget(); bdy.setStyleSheet("background: transparent;")
            bl = QVBoxLayout(bdy); bl.setContentsMargins(16, 12, 16, 12); bl.setSpacing(12)
            
            # Barrier & Plate display
            b_row = QHBoxLayout(); b_row.setSpacing(16)
            
            # Barrier Arm Circle (mimic .barrier-arm.closed)
            from PySide6.QtSvgWidgets import QSvgWidget
            b_arm_cont = QFrame()
            b_arm_cont.setFixedSize(60, 60)
            b_arm_lay = QHBoxLayout(b_arm_cont)
            b_arm_lay.setContentsMargins(0, 0, 0, 0)
            b_arm_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_arm = QSvgWidget()
            b_arm.setFixedSize(32, 32)
            b_arm_lay.addWidget(b_arm)
            b_row.addWidget(b_arm_cont)
            
            p_col = QVBoxLayout(); p_col.setSpacing(4)
            status_lbl = label("⚫ Chờ xe", style="font-weight: bold; color: #1e293b; font-size: 13px;")
            p_col.addWidget(status_lbl)
            plate = label("—"); plate.setAlignment(Qt.AlignmentFlag.AlignCenter)
            plate.setStyleSheet("background: #fffbeb; border: 3px solid #f59e0b; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 24px; font-weight: 900; color: #1e293b; min-height: 48px; letter-spacing: 2px;")
            p_col.addWidget(plate); b_row.addLayout(p_col)
            bl.addLayout(b_row)
            self.lane_plate.append(plate)
            self.lane_b_arm[lane.id] = (b_arm, b_arm_cont)
            self.lane_status_lbl[lane.id] = status_lbl
            self._set_barrier_state(lane.id, "CLOSED")
            
            # Camera View
            cam = QLabel("📷\nCamera đang chờ..."); cam.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cam.setStyleSheet("background: #000000; color: #22c55e; font-family: monospace; font-size: 12px; border-radius: 8px; min-height: 140px;")
            bl.addWidget(cam)
            
            # Devices
            d_row = QHBoxLayout(); d_row.setSpacing(6)
            for d in ["Thẻ RFID", "Camera", "Barrier"]:
                d_row.addWidget(label(d, style="background: #dcfce7; color: #16a34a; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: 700; opacity: 0.75;"))
            d_row.addStretch(); bl.addLayout(d_row)
            cbox.addWidget(bdy)
            
            # Footer / Actions
            ftr = QWidget(); ftr.setStyleSheet("background: #f8fafc; border-top: 1px solid #e2e8f0; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;")
            fl = QVBoxLayout(ftr); fl.setContentsMargins(16, 12, 16, 12); fl.setSpacing(8)
            
            in_row1 = QHBoxLayout(); in_row1.setSpacing(8)
            uid = QLineEdit(); uid.setPlaceholderText("Mã thẻ (UID)"); uid.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 8px; font-size: 12px; height: 28px;")
            pl = QLineEdit(); pl.setPlaceholderText("Biển số"); pl.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 8px; font-size: 12px; height: 28px;")
            in_row1.addWidget(uid, 7); in_row1.addWidget(pl, 5); fl.addLayout(in_row1)
            
            btn_row = QHBoxLayout(); btn_row.setSpacing(8)
            btn_in = QPushButton("→\nVào"); btn_in.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_in.setStyleSheet("background: #22c55e; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 12px; height: 50px;")
            btn_in.clicked.connect(lambda _=False, lane_id=lane.id, u=uid, p=pl: self.record_entry(lane_id, u, p))
            
            btn_out = QPushButton("←\nRa"); btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_out.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 12px; height: 50px;")
            btn_out.clicked.connect(lambda _=False, lane_id=lane.id, u=uid, p=pl: self.record_exit(lane_id, u, p))
            
            btn_issue = QPushButton("💳\nCấp thẻ"); btn_issue.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_issue.setStyleSheet("background: #f59e0b; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 12px; height: 50px;")
            btn_issue.clicked.connect(lambda _=False, lane_id=lane.id, u=uid, p=pl: self.issue_card(lane_id, u, p))
            
            btn_row.addWidget(btn_in); btn_row.addWidget(btn_out); btn_row.addWidget(btn_issue); fl.addLayout(btn_row)
            
            man_row = QHBoxLayout(); man_row.setSpacing(8)
            bm_op = QPushButton("🔓 Mở tay"); bm_op.setCursor(Qt.CursorShape.PointingHandCursor); bm_op.setStyleSheet("background: transparent; color: #16a34a; border: 1px solid #22c55e; border-radius: 4px; font-size: 11px; padding: 4px;")
            bm_op.clicked.connect(lambda _=False, lane_id=lane.id: self.manual_open(lane_id))
            
            bm_cl = QPushButton("🔒 Đóng"); bm_cl.setCursor(Qt.CursorShape.PointingHandCursor); bm_cl.setStyleSheet("background: transparent; color: #475569; border: 1px solid #94a3b8; border-radius: 4px; font-size: 11px; padding: 4px;")
            bm_cl.clicked.connect(lambda _=False, lane_id=lane.id: self.manual_close(lane_id))
            
            bm_cp = QPushButton("📷 Chụp"); bm_cp.setCursor(Qt.CursorShape.PointingHandCursor); bm_cp.setStyleSheet("background: transparent; color: #0284c7; border: 1px solid #38bdf8; border-radius: 4px; font-size: 11px; padding: 4px;")
            bm_cp.clicked.connect(lambda _=False, lane_id=lane.id: self.trigger_camera(lane_id))
            man_row.addWidget(bm_op); man_row.addWidget(bm_cl); man_row.addWidget(bm_cp); fl.addLayout(man_row)
            
            cbox.addWidget(ftr)
            self.lane_cards.append((lane.name, card))
        
        do_filter("— Tất cả làn —")
        self.refresh_live()
        
        return page

    def setup_shift_ui(self):
        if hasattr(self, 'shift_id') and self.shift_id:
            self.shift_button.setText("⏹ Đóng ca")
            self.shift_button.setStyleSheet("background: #ef4444; color: white; border-radius: 6px; padding: 6px 16px; font-weight: bold;")
            try: self.shift_button.clicked.disconnect()
            except: pass
            self.shift_button.clicked.connect(self.close_shift)
            self.shift_status_badge.setText("Ca đang hoạt động"); self.shift_status_badge.setStyleSheet("background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; padding: 4px 12px;")
        else:
            self.shift_button.setText("▶ Mở ca")
            self.shift_button.setStyleSheet("background: #22c55e; color: white; border-radius: 6px; padding: 6px 16px; font-weight: bold;")
            try: self.shift_button.clicked.disconnect()
            except: pass
            self.shift_button.clicked.connect(self.open_shift)
            self.shift_status_badge.setText("Chưa mở ca"); self.shift_status_badge.setStyleSheet("background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; padding: 4px 12px;")

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
                self.setup_shift_ui()
            save.clicked.connect(do_open); dialog.exec()

    def close_shift(self) -> None:
        if not getattr(self, 'shift_id', None): return
        cash_str, ok = QInputDialog.getText(self, "Đóng ca", "Tiền cuối ca thực tế (VNĐ):", text="0")
        if not ok: return
        try: cash = int(cash_str.replace(".", "").replace(",", ""))
        except: cash = 0
        try:
            asyncio.run(_close_shift(self.settings, getattr(self.user, "user_id"), cash, ""))
            show_toast(self, f"Đã đóng ca thành công", "success")
            self.shift_id = None
            self.setup_shift_ui()
            self.refresh_live()
            self.reload_page("shifts")
        except Exception as exc: show_toast(self, str(exc), "error")

    def issue_card(self, lane_id: str, uid_input: QLineEdit, plate_input: QLineEdit) -> None:
        if not getattr(self, 'shift_id', None):
            show_toast(self, "Hãy mở ca làm việc trước.", "error"); return
        
        dialog, content, footer = modal_shell(self, "Cấp thẻ vãng lai", 400)
        content.addWidget(label("Xe đến làn chưa có thẻ. Cấp thẻ vãng lai để tiếp tục.", "muted"))
        
        grid = QGridLayout()
        grid.addWidget(label("Chọn thẻ trống *", bold=True), 0, 0)
        card_cb = QComboBox()
        try:
            avail_cards = asyncio.run(_get_available_guest_cards(self.settings))
            for c in avail_cards: card_cb.addItem(c)
        except Exception: pass
        if card_cb.count() == 0: show_toast(self, "Không có thẻ vãng lai trống nào!", "error"); return
        grid.addWidget(card_cb, 1, 0)
        
        grid.addWidget(label("Biển số xe", bold=True), 2, 0)
        plate_in = QLineEdit(); plate_in.setText(plate_input.text().strip())
        grid.addWidget(plate_in, 3, 0)
        
        grid.addWidget(label("Loại xe", bold=True), 4, 0)
        vtype_cb = QComboBox()
        try:
            vtypes = asyncio.run(_vehicle_types(self.settings))
            for v in vtypes: vtype_cb.addItem(v.display_name, v.code)
        except Exception: pass
        grid.addWidget(vtype_cb, 5, 0)
        content.addLayout(grid)
        
        cancel = QPushButton("Hủy"); cancel.clicked.connect(dialog.reject)
        issue = QPushButton("Cấp thẻ & Mở barrier"); issue.setObjectName("info")
        footer.addWidget(cancel); footer.addWidget(issue)
        
        def do_issue():
            c_uid = card_cb.currentText(); p = plate_in.text().strip(); vc = vtype_cb.currentData()
            try:
                asyncio.run(_entry(self.settings, lane_id, p, vc, self.shift_id, c_uid))
                show_toast(self, f"Đã cấp thẻ {c_uid} và mở barrier", "success")
                uid_input.clear(); plate_input.clear(); self.refresh_live(); dialog.accept()
            except Exception as e: show_toast(self, str(e), "error")
        issue.clicked.connect(do_issue); dialog.exec()

    def _set_barrier_state(self, lane_id: str, state: str) -> None:
        if lane_id not in self.lane_b_arm: return
        b_arm, b_arm_cont = self.lane_b_arm[lane_id]
        status_lbl = self.lane_status_lbl[lane_id]
        
        SVG_CLOSED = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="#dc2626"><path d="M400 480H112c-26.5 0-48-21.5-48-48V112c0-26.5 21.5-48 48-48h288c26.5 0 48 21.5 48 48v320c0 26.5-21.5 48-48 48zM176 272c0-13.3-10.7-24-24-24s-24 10.7-24 24 10.7 24 24 24 24-10.7 24-24z"/></svg>'
        SVG_OPEN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="#16a34a"><path d="M400 480H112c-26.5 0-48-21.5-48-48V112c0-26.5 21.5-48 48-48h288c26.5 0 48 21.5 48 48v320c0 26.5-21.5 48-48 48zM176 272c0-13.3-10.7-24-24-24s-24 10.7-24 24 10.7 24 24 24 24-10.7 24-24zm160-24c0-13.3-10.7-24-24-24h-64c-13.3 0-24 10.7-24 24s10.7 24 24 24h64c13.3 0 24-10.7 24-24z"/></svg>'
        
        if state == "OPEN":
            b_arm.load(SVG_OPEN.encode('utf-8'))
            b_arm_cont.setStyleSheet("background: #dcfce7; border: 3px solid #16a34a; border-radius: 30px;")
            status_lbl.setText("🟢 Barrier đang mở")
        else:
            b_arm.load(SVG_CLOSED.encode('utf-8'))
            b_arm_cont.setStyleSheet("background: #fef2f2; border: 3px solid #dc2626; border-radius: 30px;")
            status_lbl.setText("⚫ Chờ xe")

    def _trigger_barrier(self, lane_id: str) -> None:
        self._set_barrier_state(lane_id, "OPEN")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._set_barrier_state(lane_id, "CLOSED"))

    def manual_open(self, lane_id: str): 
        show_toast(self, "Đã gửi lệnh MỞ barrier thủ công", "info")
        self._trigger_barrier(lane_id)
    def manual_close(self, lane_id: str): show_toast(self, "Đã gửi lệnh ĐÓNG barrier", "info")
    def trigger_camera(self, lane_id: str): show_toast(self, "Đã gửi lệnh kích hoạt CAMERA", "info")

    def record_entry(self, lane_id: str, uid_input: QLineEdit, plate_input: QLineEdit) -> None:
            if not self.shift_id: show_toast(self, "Hãy mở ca làm việc trước.", "error"); return
            card_uid = uid_input.text().strip()
            plate = plate_input.text().strip()
            if not card_uid and not plate:
                show_toast(self, "Vui lòng nhập UID thẻ hoặc Biển số", "warning"); return
            try:
                vehicle_types = asyncio.run(_vehicle_types(self.settings))
                vehicle_code = vehicle_types[0].code if vehicle_types else "xe_may"
            except Exception: vehicle_code = "xe_may"
            try: 
                asyncio.run(_entry(self.settings, lane_id, plate, vehicle_code, self.shift_id, card_uid))
                show_toast(self, f"Xe vào thành công (Thẻ: {card_uid or 'Cấp tay'}, Biển: {plate or '---'})", "success")
                uid_input.clear(); plate_input.clear()
                self._trigger_barrier(lane_id)
                self.refresh_live()
            except Exception as exc: show_toast(self, str(exc), "error")

    def record_exit(self, lane_id: str, uid_input: QLineEdit, plate_input: QLineEdit) -> None:
            card_uid = uid_input.text().strip()
            plate = plate_input.text().strip()
            if not card_uid and not plate:
                show_toast(self, "Vui lòng nhập UID thẻ hoặc Biển số", "warning"); return
            try: 
                fee, minutes = asyncio.run(_exit(self.settings, lane_id, plate, card_uid))
                show_toast(self, f"Xe ra thành công!\nPhí: {fee:,} VND\nThời gian: {minutes} phút", "success")
                uid_input.clear(); plate_input.clear()
                self._trigger_barrier(lane_id)
                self.refresh_live()
            except Exception as exc: show_toast(self, str(exc), "error")

    def refresh_live(self) -> None:
            try: stats = asyncio.run(_stats(self.settings, getattr(self, 'shift_id', None)))
            except Exception: return
            
            active_cnt = stats['active']
            today_cnt = stats['today_count']
            revenue = stats['revenue']
            alerts_cnt = stats.get('alerts', 0)
            
            # Update Financial Bar in Operations Page
            if hasattr(self, "lbl_in_lot"):
                self.lbl_in_lot.setText(str(active_cnt))
                self.lbl_rev_today.setText(f"{revenue:,} đ")
                self.lbl_rev_shift.setText(f"{revenue:,} đ") # Sync with today for now
                self.lbl_count_today.setText(str(today_cnt))
                self.lbl_start_cash.setText("0 đ")

            if hasattr(self, "overview_values") and len(self.overview_values) >= 4:
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
                        type_item = QTableWidgetItem("Thuê bao" if sess.get("subscriber_id") else "Vãng lai")
                        type_item.setForeground(__import__('PySide6.QtGui', fromlist=['QColor']).QColor("#2563eb" if sess.get("subscriber_id") else "#16a34a"))
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

