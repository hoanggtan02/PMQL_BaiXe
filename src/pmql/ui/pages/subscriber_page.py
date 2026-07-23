from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class SubscriberPageMixin:
    def subscriber_page(self) -> QWidget:
        page, box = self.page()
        
        # Header row
        header_row = QHBoxLayout()
        title = label("Quản lý thuê bao", bold=True)
        title.setStyleSheet("font-size:24px;")
        header_row.addWidget(title)
        header_row.addStretch()
        
        add_btn = QPushButton("+ Thêm thuê bao")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self.add_subscriber)
        header_row.addWidget(add_btn)
        box.addLayout(header_row)
        box.addSpacing(8)
        
        # Filter row (Search + Status)
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Tìm tên, SĐT, biển số...")
        search_input.setFixedWidth(240)
        search_input.textChanged.connect(self.filter_subscribers)
        self.subscriber_search_input = search_input
        filter_row.addWidget(search_input)
        
        status_combo = QComboBox()
        status_combo.addItem("Tất cả trạng thái", "")
        status_combo.addItem("Hoạt động", "ACTIVE")
        status_combo.addItem("Đã khóa", "LOCKED")
        status_combo.addItem("Sắp hết hạn (7 ngày)", "EXPIRING")
        status_combo.setFixedWidth(180)
        status_combo.currentIndexChanged.connect(self.filter_subscribers)
        self.subscriber_status_combo = status_combo
        filter_row.addWidget(status_combo)
        
        filter_row.addStretch()
        box.addLayout(filter_row)
        box.addSpacing(10)
        
        # Table with 7 headers matching web app v1: Họ tên, Số điện thoại, Biển số xe, Hiệu lực đến, Còn lại, Trạng thái, Thao tác
        headers = ["Họ tên", "Số điện thoại", "Biển số xe", "Hiệu lực đến", "Còn lại", "Trạng thái", "Thao tác"]
        self.subscriber_table = self.make_table(headers, action_col_width=180)
        self.subscriber_table.cellClicked.connect(self.on_table_cell_clicked)
        box.addWidget(self.subscriber_table, 1)
        
        self.load_subscribers()
        return page

    def load_subscribers(self) -> None:
        if not hasattr(self, "subscriber_table"): return
        try:
            data = asyncio.run(_subscriber_with_vehicles(self.settings))
        except Exception: return
        
        self.raw_subscribers_data = data
        self.filter_subscribers()

    def filter_subscribers(self) -> None:
        if not hasattr(self, "raw_subscribers_data"): return
        
        query = getattr(self, "subscriber_search_input", QLineEdit()).text().strip().lower()
        status_filter = getattr(self, "subscriber_status_combo", QComboBox()).currentData()
        
        filtered = []
        today_date = date.today()
        
        for item, vehicles in self.raw_subscribers_data:
            name_match = query in item.full_name.lower()
            phone_match = query in (item.phone or "").lower()
            plate_match = any(query in v.plate_number.lower() for v in vehicles)
            
            if query and not (name_match or phone_match or plate_match):
                continue
                
            valid_until_date = item.valid_until if isinstance(item.valid_until, date) else date.fromisoformat(str(item.valid_until))
            days_left = (valid_until_date - today_date).days
            
            if status_filter == "ACTIVE" and not item.is_active:
                continue
            elif status_filter == "LOCKED" and item.is_active:
                continue
            elif status_filter == "EXPIRING" and not (0 <= days_left <= 7):
                continue
                
            filtered.append((item, vehicles))
            
        self.render_subscriber_table(filtered)

    def render_subscriber_table(self, data: list) -> None:
        self.displayed_subscribers = data
        self.subscriber_table.setRowCount(len(data))
        today_date = date.today()
        
        for r, (item, vehicles) in enumerate(data):
            # Col 0: Họ tên
            name_item = QTableWidgetItem(item.full_name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            font = name_item.font()
            if font.pointSize() <= 0 and font.pixelSize() <= 0: font.setPointSize(10)
            font.setBold(True)
            name_item.setFont(font)
            self.subscriber_table.setItem(r, 0, name_item)
            
            # Col 1: Số điện thoại
            phone_item = QTableWidgetItem(item.phone or "—")
            phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.subscriber_table.setItem(r, 1, phone_item)
            
            # Col 2: Biển số xe (Yellow badges matching screenshot)
            w_plates = QWidget()
            lay_plates = QHBoxLayout(w_plates)
            lay_plates.setContentsMargins(4, 4, 4, 4)
            lay_plates.setSpacing(6)
            lay_plates.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if vehicles:
                for v in vehicles:
                    lbl = QLabel(v.plate_number)
                    lbl.setStyleSheet("background: #fef08a; color: #854d0e; border: 1px solid #fde047; border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 12px;")
                    lay_plates.addWidget(lbl)
            else:
                lbl_none = QLabel("—")
                lbl_none.setStyleSheet("color: #94a3b8;")
                lay_plates.addWidget(lbl_none)
            self.subscriber_table.setItem(r, 2, QTableWidgetItem(""))
            w_plates.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.subscriber_table.setCellWidget(r, 2, w_plates)
            
            # Col 3: Hiệu lực đến
            valid_until_date = item.valid_until if isinstance(item.valid_until, date) else date.fromisoformat(str(item.valid_until))
            valid_item = QTableWidgetItem(valid_until_date.isoformat())
            valid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.subscriber_table.setItem(r, 3, valid_item)
            
            # Col 4: Còn lại (Pill badges matching screenshot)
            days_left = (valid_until_date - today_date).days
            w_days = QWidget()
            lay_days = QHBoxLayout(w_days)
            lay_days.setContentsMargins(4, 4, 4, 4)
            lay_days.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if days_left < 0:
                badge_lbl = QLabel(f"Hết hạn {abs(days_left)} ngày")
                badge_lbl.setStyleSheet("background: #ef4444; color: white; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
            elif days_left < 8:
                badge_lbl = QLabel(f"Còn {days_left} ngày")
                badge_lbl.setStyleSheet("background: #f59e0b; color: white; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
            else:
                badge_lbl = QLabel(f"Còn {days_left} ngày")
                badge_lbl.setStyleSheet("background: #10b981; color: white; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
            lay_days.addWidget(badge_lbl)
            self.subscriber_table.setItem(r, 4, QTableWidgetItem(""))
            w_days.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.subscriber_table.setCellWidget(r, 4, w_days)
            
            # Col 5: Trạng thái (Pill badges matching screenshot)
            w_status = QWidget()
            lay_status = QHBoxLayout(w_status)
            lay_status.setContentsMargins(4, 4, 4, 4)
            lay_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_s = QLabel("Hoạt động" if item.is_active else "Đã khóa")
            if item.is_active:
                lbl_s.setStyleSheet("background: #10b981; color: white; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
            else:
                lbl_s.setStyleSheet("background: #64748b; color: white; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;")
            lay_status.addWidget(lbl_s)
            self.subscriber_table.setItem(r, 5, QTableWidgetItem(""))
            w_status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.subscriber_table.setCellWidget(r, 5, w_status)
            
            # Col 6: Thao tác (Actions)
            actions = QWidget(); actions.setMinimumHeight(38)
            row_lay = QHBoxLayout(actions); row_lay.setContentsMargins(6, 4, 6, 4); row_lay.setSpacing(6); row_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
            remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
            edit.clicked.connect(lambda _=False, subscriber=item, vlist=vehicles: self.subscriber_dialog(subscriber, vlist))
            remove.clicked.connect(lambda _=False, subscriber=item: self.delete_subscriber(subscriber))
            row_lay.addWidget(edit); row_lay.addWidget(remove)
            self.subscriber_table.setItem(r, 6, QTableWidgetItem(""))
            self.subscriber_table.setCellWidget(r, 6, actions)
            self.subscriber_table.setRowHeight(r, 56)

    def on_table_cell_clicked(self, row: int, col: int) -> None:
        if col == 6: return
        if hasattr(self, "displayed_subscribers") and 0 <= row < len(self.displayed_subscribers):
            subscriber, vehicles = self.displayed_subscribers[row]
            self.subscriber_detail_dialog(subscriber, vehicles)

    def subscriber_detail_dialog(self, subscriber, vehicles) -> None:
        dialog, content, footer = modal_shell(self, "Chi tiết thuê bao", 560)
        
        info_grid = QGridLayout()
        info_grid.setSpacing(12)
        info_grid.setColumnStretch(0, 1)
        info_grid.setColumnStretch(1, 1)
        content.addLayout(info_grid)
        
        info_grid.addWidget(label("Họ tên", "muted"), 0, 0)
        info_grid.addWidget(label(subscriber.full_name, bold=True), 1, 0)
        
        info_grid.addWidget(label("SĐT", "muted"), 0, 1)
        info_grid.addWidget(label(subscriber.phone or "—"), 1, 1)
        
        info_grid.addWidget(label("Hiệu lực từ", "muted"), 2, 0)
        info_grid.addWidget(label(subscriber.valid_from.isoformat() if hasattr(subscriber.valid_from, "isoformat") else str(subscriber.valid_from)), 3, 0)
        
        info_grid.addWidget(label("Hiệu lực đến", "muted"), 2, 1)
        
        valid_until_date = subscriber.valid_until if isinstance(subscriber.valid_until, date) else date.fromisoformat(str(subscriber.valid_until))
        today_date = date.today()
        days_left = (valid_until_date - today_date).days
        
        valid_until_box = QHBoxLayout()
        valid_until_box.setContentsMargins(0, 0, 0, 0)
        valid_until_box.addWidget(label(valid_until_date.isoformat()))
        
        if days_left < 0:
            badge_text = f"Hết hạn {abs(days_left)} ngày"
            badge_style = "background: #ef4444; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
        elif days_left < 8:
            badge_text = f"Còn {days_left} ngày"
            badge_style = "background: #f59e0b; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
        else:
            badge_text = f"Còn {days_left} ngày"
            badge_style = "background: #10b981; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
            
        badge_lbl = QLabel(badge_text)
        badge_lbl.setStyleSheet(badge_style)
        valid_until_box.addWidget(badge_lbl)
        valid_until_box.addStretch()
        
        w_valid = QWidget(); w_valid.setLayout(valid_until_box)
        info_grid.addWidget(w_valid, 3, 1)
        
        content.addSpacing(10)
        content.addWidget(label("Phương tiện", "muted"))
        
        v_box = QHBoxLayout(); v_box.setContentsMargins(0, 0, 0, 0); v_box.setSpacing(10)
        if vehicles:
            vehicle_names = asyncio.run(_vehicle_name_map(self.settings))
            for v in vehicles:
                badge = QLabel(v.plate_number)
                badge.setStyleSheet("background: #fef08a; color: #854d0e; font-weight: bold; border-radius: 4px; padding: 4px 10px; font-size: 13px; border: 1px solid #fde047;")
                v_type_str = vehicle_names.get(v.vehicle_type, v.vehicle_type)
                type_lbl = QLabel(f"• {v_type_str}")
                type_lbl.setStyleSheet("color: #64748b; font-size: 12px;")
                v_box.addWidget(badge)
                v_box.addWidget(type_lbl)
                v_box.addSpacing(10)
        else:
            v_box.addWidget(label("Chưa đăng ký xe nào", "muted"))
        v_box.addStretch()
        w_v = QWidget(); w_v.setLayout(v_box)
        content.addWidget(w_v)
        
        content.addSpacing(10)
        content.addWidget(label("Thẻ được cấp", "muted"))
        
        cards = asyncio.run(_get_cards_for_subscriber(self.settings, subscriber.id))
        c_box = QHBoxLayout(); c_box.setContentsMargins(0, 0, 0, 0); c_box.setSpacing(10)
        if cards:
            for c in cards:
                c_code = QLabel(c.card_number if hasattr(c, "card_number") else getattr(c, "code", getattr(c, "id", "")))
                c_code.setStyleSheet("background: #f1f5f9; color: #334155; font-family: monospace; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
                c_status = QLabel("Hoạt động" if getattr(c, "status", "") in ("IN_USE", "AVAILABLE") else "Đã khóa")
                c_status.setStyleSheet("background: #dcfce7; color: #15803d; border-radius: 4px; padding: 2px 6px; font-size: 11px;")
                c_box.addWidget(c_code)
                c_box.addWidget(c_status)
                c_box.addSpacing(10)
        else:
            c_box.addWidget(label("—", "muted"))
        c_box.addStretch()
        w_c = QWidget(); w_c.setLayout(c_box)
        content.addWidget(w_c)
        
        content.addSpacing(10)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;")
        content.addWidget(sep)
        content.addSpacing(10)
        
        lbl_renew = label("Gia hạn đến ngày", bold=True)
        lbl_renew.setStyleSheet("color: #475569; font-size: 13px;")
        
        default_renew_date = max(valid_until_date, date.today()) + timedelta(days=30)
        renew_date_edit = QDateEdit(default_renew_date)
        renew_date_edit.setCalendarPopup(True)
        renew_date_edit.setDisplayFormat("dd/MM/yyyy")
        renew_date_edit.setFixedWidth(120)
        renew_date_edit.setStyleSheet("QDateEdit { border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; }")
        
        cancel = QPushButton("Đóng")
        cancel.clicked.connect(dialog.reject)
        
        save = icon_btn("fa5s.calendar-plus", "Gia hạn", "QPushButton { background: #10b981; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px; font-weight: bold; } QPushButton:hover { background: #059669; }")
        
        def do_renew():
            new_date_iso = renew_date_edit.date().toPython().isoformat()
            try:
                asyncio.run(_extend_subscriber(self.settings, subscriber.id, new_date_iso))
                show_toast(self, f"Đã gia hạn thành công cho {subscriber.full_name} đến {new_date_iso}", "info")
                dialog.accept()
                self.load_subscribers()
            except Exception as exc:
                show_toast(dialog, f"Không thể gia hạn: {exc}", "error")
                
        save.clicked.connect(do_renew)
        
        footer.addWidget(lbl_renew)
        footer.addWidget(renew_date_edit)
        footer.addStretch()
        footer.addWidget(cancel)
        footer.addWidget(save)
        
        dialog.exec()

    def add_subscriber(self) -> None:
        self.subscriber_dialog()

    def edit_subscriber(self, subscriber, vehicles) -> None:
        self.subscriber_dialog(subscriber, vehicles)

    def subscriber_dialog(self, subscriber=None, vehicles=None) -> None:
        dialog, content, footer = modal_shell(self, "Thêm thuê bao" if not subscriber else "Sửa thuê bao", 720)
        
        grid = QGridLayout(); content.addLayout(grid)
        
        name = QLineEdit(subscriber.full_name if subscriber else "")
        phone = QLineEdit(subscriber.phone if subscriber else "")
        email = QLineEdit(subscriber.email or "" if subscriber else "")
        identity_card = QLineEdit(getattr(subscriber, "identity_card", "") if subscriber else "")
        start = QDateEdit(subscriber.valid_from if subscriber else date.today()); start.setCalendarPopup(True)
        end = QDateEdit(subscriber.valid_until if subscriber else date.today().replace(year=date.today().year + 1)); end.setCalendarPopup(True)
        
        grid.addWidget(label("Họ và tên *", "muted"), 0, 0); grid.addWidget(name, 1, 0)
        grid.addWidget(label("Số điện thoại *", "muted"), 2, 0); grid.addWidget(phone, 3, 0)
        grid.addWidget(label("Email", "muted"), 4, 0); grid.addWidget(email, 5, 0)
        grid.addWidget(label("CMND/CCCD", "muted"), 6, 0); grid.addWidget(identity_card, 7, 0)
        grid.addWidget(label("Hiệu lực từ", "muted"), 8, 0); grid.addWidget(start, 9, 0)
        grid.addWidget(label("Hiệu lực đến", "muted"), 10, 0); grid.addWidget(end, 11, 0)
        
        if subscriber:
            active = QComboBox(); active.addItem("Hoạt động", True); active.addItem("Đã khóa", False)
            active.setCurrentIndex(0 if subscriber.is_active else 1)
            grid.addWidget(label("Trạng thái", "muted"), 12, 0); grid.addWidget(active, 13, 0)

        vehicle_group = QGroupBox("Phương tiện đăng ký"); grid.addWidget(vehicle_group, 0, 1, 14, 1)
        vehicle_group.setStyleSheet("QGroupBox { margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #475569; }")
        v_layout = QVBoxLayout(vehicle_group)
        vehicle_list_layout = QVBoxLayout()
        v_layout.addLayout(vehicle_list_layout)
        v_layout.addStretch()
        
        add_v_btn = QPushButton("+ Thêm xe"); add_v_btn.setStyleSheet("background: #f1f5f9; color: #475569; border-radius: 4px; padding: 6px;")
        v_layout.addWidget(add_v_btn)
        
        vehicle_widgets = []
        
        def add_vehicle_row(plate="", v_type=""):
            row_w = QWidget(); r_lay = QHBoxLayout(row_w); r_lay.setContentsMargins(0,0,0,0)
            p_input = QLineEdit(plate); p_input.setPlaceholderText("Biển số")
            t_input = QComboBox(); self.fill_vehicle_combo(t_input)
            if v_type:
                idx = t_input.findData(v_type)
                if idx >= 0: t_input.setCurrentIndex(idx)
            del_btn = QPushButton("✕"); del_btn.setObjectName("danger"); del_btn.setFixedWidth(30)
            def remove_self():
                vehicle_list_layout.removeWidget(row_w); row_w.deleteLater(); vehicle_widgets.remove((p_input, t_input))
            del_btn.clicked.connect(remove_self)
            r_lay.addWidget(p_input); r_lay.addWidget(t_input); r_lay.addWidget(del_btn)
            vehicle_list_layout.addWidget(row_w)
            vehicle_widgets.append((p_input, t_input))
            
        if vehicles:
            for v in vehicles:
                add_vehicle_row(v.plate_number, v.vehicle_type)
        else:
            add_vehicle_row()
            
        add_v_btn.clicked.connect(lambda: add_vehicle_row())
        
        cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi" if subscriber else "Thêm thuê bao"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
        
        def save_item() -> None:
            v_data = [{"plate_number": p.text().strip(), "vehicle_type": t.currentData()} for p, t in vehicle_widgets if p.text().strip()]
            try:
                if subscriber:
                    asyncio.run(_update_subscriber(self.settings, subscriber.id, name.text(), phone.text(), email.text() or None, identity_card.text(), v_data, start.date().toPython().isoformat(), end.date().toPython().isoformat(), bool(active.currentData())))
                else:
                    asyncio.run(_create_subscriber(self.settings, name.text(), phone.text(), email.text() or None, identity_card.text(), v_data, start.date().toPython().isoformat(), end.date().toPython().isoformat(), None))
                self.load_subscribers(); dialog.accept()
            except Exception as exc: show_toast(dialog, str(exc), "error")
        save.clicked.connect(save_item); dialog.exec()

    def delete_subscriber(self, subscriber) -> None:
        if QMessageBox.question(self, "Xóa thuê bao", f"Xóa mềm thuê bao '{subscriber.full_name}'?") != QMessageBox.StandardButton.Yes: return
        try: asyncio.run(_delete_subscriber(self.settings, subscriber.id)); self.load_subscribers()
        except Exception as exc: show_toast(self, str(exc), "error")
