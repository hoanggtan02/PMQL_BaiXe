"""Patch script to rewrite fee_page and related fee rule functions to perfectly match the requested design."""
import sys

NEW_FEE_PAGE = '''        def show_fee_history(self):
            dialog, content, footer = modal_shell(self, "Lịch sử các quy tắc phí", 800)
            from PySide6.QtGui import QColor as _QColor
            hist_tbl = self.make_table(
                ["Quy tắc", "Loại xe", "Giá/block", "Block", "Miễn phí", "Trần/ngày", "Trạng thái"],
                action_col_width=130
            )
            try:
                snap_rules = asyncio.run(_fee_rules(settings))
                snap_names = asyncio.run(_vehicle_name_map(settings))
                hist_tbl.setRowCount(len(snap_rules))
                for ri, sr in enumerate(snap_rules):
                    vals = (
                        sr.name,
                        snap_names.get(sr.vehicle_type, sr.vehicle_type),
                        f"{sr.price_per_block:,} đ",
                        f"{sr.block_minutes} phút",
                        f"{sr.free_minutes} phút",
                        f"{sr.day_max:,} đ" if sr.day_max else "--",
                    )
                    for ci, val in enumerate(vals):
                        itm = QTableWidgetItem(val)
                        itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        hist_tbl.setItem(ri, ci, itm)
                    status_itm = QTableWidgetItem(
                        "Đang áp dụng" if sr.is_active else "Đã tắt"
                    )
                    status_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    status_itm.setForeground(
                        _QColor("#166534" if sr.is_active else "#94a3b8")
                    )
                    hist_tbl.setItem(ri, 6, status_itm)
            except Exception:
                pass
            content.addWidget(hist_tbl)
            close = QPushButton("Đóng"); close.clicked.connect(dialog.reject)
            footer.addStretch(); footer.addWidget(close)
            dialog.exec()

        def fee_page(self) -> QWidget:
            page, box = self.page()
            
            # Header
            hrow = QHBoxLayout()
            hist_btn = icon_btn("fa5s.history", "Lịch sử thay đổi", "QPushButton { background: white; color: #64748b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 12px; } QPushButton:hover { background: #f1f5f9; }")
            hist_btn.clicked.connect(self.show_fee_history)
            hrow.addWidget(hist_btn); hrow.addStretch()
            
            add_btn = icon_btn("fa5s.plus", "Thêm quy tắc phí", _BTN_EDIT_STYLE.replace("#3b82f6", "#f97316")) # Orange
            add_btn.clicked.connect(self.add_fee_rule)
            hrow.addWidget(add_btn)
            box.addLayout(hrow)

            # Grid of rules
            try:
                rules = asyncio.run(_fee_rules(settings))
                vehicle_names = asyncio.run(_vehicle_name_map(settings))
            except Exception:
                rules = []; vehicle_names = {}

            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            grid_w = QWidget(); grid = QGridLayout(grid_w)
            grid.setSpacing(14); grid.setAlignment(Qt.AlignmentFlag.AlignTop)

            VICONS = {"xe_may": "🛵", "o_to": "🚗", "xe_dap": "🚲", "xe_tai": "🚚"}

            for index, rule in enumerate(rules):
                f = QFrame(); f.setObjectName("fee_card")
                is_active = rule.is_active
                border_color = "#facc15" if is_active else "#e2e8f0"
                f.setStyleSheet(
                    f"QFrame#fee_card {{ background: white; border: 1px solid {border_color};"
                    f" border-radius: 8px; }}"
                )
                c = QVBoxLayout(f); c.setSpacing(12); c.setContentsMargins(16, 14, 16, 14)

                # Title row
                t_row = QHBoxLayout()
                vicon = VICONS.get(rule.vehicle_type, "🚗")
                name_lbl = label(f"{vicon} {rule.name}", bold=True)
                name_lbl.setStyleSheet("font-size:14px; color:#1e293b;")
                t_row.addWidget(name_lbl); t_row.addStretch()

                if is_active:
                    badge = label("Đang áp dụng")
                    badge.setStyleSheet(
                        "background:#fef08a; color:#854d0e; border-radius:4px;"
                        " padding:2px 8px; font-size:11px; font-weight:bold;"
                    )
                    t_row.addWidget(badge)
                c.addLayout(t_row)
                
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color: #e2e8f0;"); c.addWidget(sep)

                # Stats grid (2 columns)
                sg = QGridLayout(); sg.setHorizontalSpacing(30); sg.setVerticalSpacing(10)

                def _stat_row(r_idx, col_idx, lbl_text, val_text, val_color="#1e293b"):
                    lbl = label(lbl_text, "muted"); lbl.setStyleSheet("color:#64748b; font-size:12px; font-weight:bold;")
                    val = label(val_text, bold=True); val.setStyleSheet(f"font-size:13px; color:{val_color};")
                    sg.addWidget(lbl, r_idx, col_idx * 2)
                    sg.addWidget(val, r_idx, col_idx * 2 + 1)
                    sg.setAlignment(val, Qt.AlignmentFlag.AlignRight)

                _stat_row(0, 0, "Giá/block", f"{rule.price_per_block:,} đ", "#16a34a")
                _stat_row(0, 1, "Block", f"{rule.block_minutes} phút")
                
                day_max_txt = f"{rule.day_max:,} đ" if rule.day_max else "Không giới hạn"
                _stat_row(1, 0, "Trần/ngày", day_max_txt)
                _stat_row(1, 1, "Miễn phí", f"{rule.free_minutes} phút")
                
                if rule.night_surcharge:
                    _stat_row(2, 1, "Phụ thu đêm", f"{rule.night_surcharge:,} đ")
                    
                c.addLayout(sg)
                
                c.addWidget(QFrame(frameShape=QFrame.Shape.HLine).setStyleSheet("color: #e2e8f0;"))

                # Actions row (Edit and Delete)
                a_row = QHBoxLayout(); a_row.setContentsMargins(0, 0, 0, 0)
                edit_btn = icon_btn("fa5s.edit", "Sửa", "QPushButton { color: #3b82f6; background: transparent; border: 1px solid #bfdbfe; border-radius: 6px; padding: 6px 12px; font-weight: bold; } QPushButton:hover { background: #eff6ff; }")
                del_btn = icon_btn("fa5s.trash-alt", "", "QPushButton { color: #ef4444; background: transparent; border: 1px solid #fecaca; border-radius: 6px; padding: 6px 10px; font-weight: bold; } QPushButton:hover { background: #fef2f2; }")
                
                edit_btn.clicked.connect(lambda _=False, item=rule: self.edit_fee_rule(item))
                del_btn.clicked.connect(lambda _=False, item=rule: self.delete_fee_rule(item))

                a_row.addWidget(edit_btn, 1) # Edit button expands
                a_row.addWidget(del_btn)
                c.addLayout(a_row)

                grid.addWidget(f, index // 3, index % 3)

            scroll.setWidget(grid_w); box.addWidget(scroll, 1)

            # Fee Calculator
            calc_frame = QFrame()
            calc_frame.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px;")
            calc_layout = QVBoxLayout(calc_frame)
            calc_layout.setContentsMargins(20, 16, 20, 16)
            
            calc_title = label("🧮 Tính phí thử", bold=True)
            calc_title.setStyleSheet("color: #d97706; font-size: 14px;")
            calc_layout.addWidget(calc_title)
            
            sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet("color: #e2e8f0;"); calc_layout.addWidget(sep2)

            cg = QGridLayout(); cg.setSpacing(16)
            cg.addWidget(label("Loại xe", "muted"), 0, 0)
            calc_vehicle = QComboBox(); self.fill_vehicle_combo(calc_vehicle)
            cg.addWidget(calc_vehicle, 1, 0)

            from PySide6.QtWidgets import QDateTimeEdit as _DTE
            from PySide6.QtCore import QDateTime as _QDT

            cg.addWidget(label("Giờ vào", "muted"), 0, 1)
            dt_in = _DTE(_QDT.currentDateTime().addSecs(-3600))
            dt_in.setDisplayFormat("dd/MM/yyyy HH:mm"); dt_in.setCalendarPopup(True)
            cg.addWidget(dt_in, 1, 1)

            cg.addWidget(label("Giờ ra", "muted"), 0, 2)
            dt_out = _DTE(_QDT.currentDateTime())
            dt_out.setDisplayFormat("dd/MM/yyyy HH:mm"); dt_out.setCalendarPopup(True)
            cg.addWidget(dt_out, 1, 2)

            calc_btn2 = QPushButton("Tính phí")
            calc_btn2.setStyleSheet("QPushButton { color: #f97316; background: transparent; border: 1px solid #fdba74; border-radius: 6px; padding: 8px 24px; font-weight: bold; } QPushButton:hover { background: #fff7ed; }")
            cg.addWidget(calc_btn2, 1, 3)
            calc_layout.addLayout(cg)
            
            # Result Label
            result_lbl = label("")
            result_lbl.setStyleSheet("color: #1e293b; font-size: 13px;")
            result_lbl.setVisible(False)
            calc_layout.addWidget(result_lbl)

            def do_calc():
                try:
                    from pmql.domain.services.fee_calculator import FeeCalculator as _FC
                    v_code = calc_vehicle.currentData()
                    all_rules = asyncio.run(_fee_rules(settings))
                    active_rules = [r for r in all_rules if r.is_active and r.vehicle_type == v_code]
                    if not active_rules:
                        result_lbl.setStyleSheet("color: #ef4444; font-size: 13px;")
                        result_lbl.setText("Không tìm thấy quy tắc phí nào đang áp dụng cho loại xe này.")
                    else:
                        rule_c = active_rules[0]
                        entry = dt_in.dateTime().toPython()
                        exit_ = dt_out.dateTime().toPython()
                        minutes = max(0, int((exit_ - entry).total_seconds() / 60))
                        calc_obj = _FC(rule_c)
                        fee = calc_obj.calculate(entry, exit_)
                        hours, mins = divmod(minutes, 60)
                        
                        result_lbl.setStyleSheet("color: #16a34a; font-size: 14px; font-weight: bold;")
                        result_lbl.setText(f"Tổng phí: {fee:,} đ (Áp dụng: {rule_c.name} - Thời gian gửi: {hours} giờ {mins} phút)")
                    result_lbl.setVisible(True)
                except Exception as exc:
                    result_lbl.setStyleSheet("color: #ef4444; font-size: 13px;")
                    result_lbl.setText(f"Lỗi: {exc}")
                    result_lbl.setVisible(True)

            calc_btn2.clicked.connect(do_calc)

            box.addWidget(calc_frame)
            return page

        def add_fee_rule(self) -> None:
            dialog, content, footer = modal_shell(self, "Thêm quy tắc phí", 620); form = QFormLayout(); content.addLayout(form)
            name, vehicle, block, price, free, surcharge, maximum = QLineEdit(), QComboBox(), QLineEdit("60"), QLineEdit("5000"), QLineEdit("0"), QLineEdit("0"), QLineEdit(); self.fill_vehicle_combo(vehicle)
            is_active_cb = QCheckBox("Đang áp dụng"); is_active_cb.setChecked(True)
            form.addRow("Tên quy tắc *", name); form.addRow("Loại xe", vehicle); form.addRow("Block tính (phút)", block); form.addRow("Giá mỗi block (VND)", price); form.addRow("Trần/ngày (VND)", maximum); form.addRow("Phụ thu đêm (VND)", surcharge); form.addRow("Miễn phí (phút đầu)", free); form.addRow("", is_active_cb)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_rule() -> None:
                try:
                    asyncio.run(_create_fee_rule(settings, name.text(), vehicle.currentData(), int(block.text()), int(price.text()), int(free.text()), int(surcharge.text()), int(maximum.text()) if maximum.text() else None, is_active_cb.isChecked())); dialog.accept(); self.reload_page("fees")
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_rule); dialog.exec()

        def edit_fee_rule(self, rule) -> None:
            dialog, content, footer = modal_shell(self, "Sửa quy tắc phí", 560); form = QFormLayout(); content.addLayout(form)
            name, vehicle, price, block, free, surcharge, maximum = QLineEdit(rule.name), QComboBox(), QLineEdit(str(rule.price_per_block)), QLineEdit(str(rule.block_minutes)), QLineEdit(str(rule.free_minutes)), QLineEdit(str(rule.night_surcharge or 0)), QLineEdit(str(rule.day_max or "")); self.fill_vehicle_combo(vehicle); vehicle.setCurrentIndex(max(0, vehicle.findData(rule.vehicle_type)))
            is_active_cb = QCheckBox("Đang áp dụng"); is_active_cb.setChecked(rule.is_active)
            form.addRow("Tên quy tắc", name); form.addRow("Loại xe", vehicle); form.addRow("Giá/block", price); form.addRow("Block (phút)", block); form.addRow("Trần/ngày", maximum); form.addRow("Phụ thu đêm", surcharge); form.addRow("Miễn phí (phút đầu)", free); form.addRow("", is_active_cb)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_rule() -> None:
                try: asyncio.run(_update_fee_rule(settings, rule.id, name.text(), vehicle.currentData(), int(block.text()), int(price.text()), int(free.text()), int(surcharge.text()), int(maximum.text()) if maximum.text() else None, is_active_cb.isChecked())); dialog.accept(); self.reload_page("fees")
                except Exception as exc: QMessageBox.warning(dialog, "Không lưu được", str(exc))
            save.clicked.connect(save_rule); dialog.exec()

        def delete_fee_rule(self, rule) -> None:
            if QMessageBox.question(self, "Xóa biểu phí", f"Xóa mềm quy tắc '{rule.name}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_fee_rule(settings, rule.id)); self.reload_page("fees")
            except Exception as exc: QMessageBox.warning(self, "Không xóa được", str(exc))
'''

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

start_marker = "        def fee_page(self) -> QWidget:\n"
end_marker = "\n        def subscriber_page(self) -> QWidget:"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print(f"MARKERS NOT FOUND: start={start_idx}, end={end_idx}")
    sys.exit(1)
    
new_content = content[:start_idx] + NEW_FEE_PAGE + content[end_idx + 1:]

with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
    f.write(new_content)
print("fee_page rewritten!")
