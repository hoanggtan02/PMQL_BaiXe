from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class SessionPageMixin:
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
                    db = Database(self.settings.local_database_url)
                    import asyncio
                    from pmql.infrastructure.persistence.sqlite.repositories import SQLiteSessionRepository, SQLiteVehicleRepository, SQLiteLaneRepository
                    
                    async def fetch():
                        async with db.session() as session:
                            s_repo = SQLiteSessionRepository(session)
                            l_repo = SQLiteLaneRepository(session)
                            
                            all_sessions = await s_repo.list_recent(self.settings.branch_id, 5000)
                            lanes = await l_repo.list_active()
                            l_map = {l.id: l.name for l in lanes}
                            
                            return all_sessions, l_map
                    
                    v_map = asyncio.run(_vehicle_name_map(self.settings))
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

