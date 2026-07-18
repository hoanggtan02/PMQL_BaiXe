"""Patch script - rewrites fee_page section in app.py."""
import re

NEW_FEE_PAGE = '''        def fee_page(self) -> QWidget:
            page, box = self.page()
            box.setSpacing(12)

            # Header
            hrow = QHBoxLayout()
            h = label("Quan ly bieu phi", bold=True); h.setStyleSheet("font-size:24px;")
            hrow.addWidget(h); hrow.addStretch()
            add_btn = icon_btn("fa5s.plus", "Them quy tac", _BTN_EDIT_STYLE)
            add_btn.clicked.connect(self.add_fee_rule)
            hrow.addWidget(add_btn)
            box.addLayout(hrow)

            # Tabs
            tabs = QTabWidget()
            tabs.setStyleSheet(
                "QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 8px; background: white; }"
                "QTabBar::tab { padding: 8px 20px; font-weight: 600; color: #64748b; border: 1px solid #e2e8f0;"
                " border-bottom: none; border-radius: 6px 6px 0 0; background: #f1f5f9; margin-right: 4px; }"
                "QTabBar::tab:selected { background: white; color: #1e293b; }"
            )

            # Tab 1: Rule cards
            rules_tab = QWidget(); rules_layout = QVBoxLayout(rules_tab)
            rules_layout.setContentsMargins(12, 12, 12, 12)
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
                border_color = "#3b82f6" if is_active else "#e2e8f0"
                f.setStyleSheet(
                    f"QFrame#fee_card {{ background: white; border: 2px solid {border_color};"
                    " border-radius: 10px; }}"
                )
                c = QVBoxLayout(f); c.setSpacing(6); c.setContentsMargins(16, 14, 16, 14)

                # Title row
                t_row = QHBoxLayout()
                vicon = VICONS.get(rule.vehicle_type, "🚗")
                name_lbl = label(f"{vicon}  {rule.name}", bold=True)
                name_lbl.setStyleSheet("font-size:15px; color:#1e293b;")
                t_row.addWidget(name_lbl); t_row.addStretch()

                if is_active:
                    badge = label("✔ Dang ap dung")
                    badge.setStyleSheet(
                        "background:#dcfce7; color:#166534; border-radius:10px;"
                        " padding:3px 10px; font-size:11px; font-weight:bold;"
                    )
                else:
                    badge = label("− Da tat")
                    badge.setStyleSheet(
                        "background:#f1f5f9; color:#64748b; border-radius:10px;"
                        " padding:3px 10px; font-size:11px; font-weight:bold;"
                    )
                t_row.addWidget(badge); c.addLayout(t_row)

                vname_lbl = label(vehicle_names.get(rule.vehicle_type, rule.vehicle_type), "muted")
                vname_lbl.setStyleSheet("color:#64748b; font-size:12px;")
                c.addWidget(vname_lbl)

                sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color: #e2e8f0;"); c.addWidget(sep)

                # Stats grid
                sg = QGridLayout(); sg.setHorizontalSpacing(20); sg.setVerticalSpacing(4)

                def _add_stat(title_s, val_s, col_n, color="#1e293b"):
                    t_l = label(title_s)
                    t_l.setStyleSheet("color:#94a3b8; font-size:10px; font-weight:bold;")
                    v_l = label(val_s, bold=True)
                    v_l.setStyleSheet(f"font-size:14px; color:{color};")
                    sg.addWidget(t_l, 0, col_n); sg.addWidget(v_l, 1, col_n)

                _add_stat("GIA/BLOCK", f"{rule.price_per_block:,} d", 0, "#2563eb")
                _add_stat("BLOCK", f"{rule.block_minutes} phut", 1)
                _add_stat("MIEN PHI", f"{rule.free_minutes} phut", 2)
                if rule.day_max:
                    _add_stat("TRAN/NGAY", f"{rule.day_max:,} d", 3, "#16a34a")
                if rule.night_surcharge:
                    _add_stat("PHU DEM", f"{rule.night_surcharge:,} d", 4, "#d97706")
                c.addLayout(sg)

                # Actions
                a_row = QHBoxLayout(); a_row.setContentsMargins(0, 6, 0, 0)
                edit_btn = icon_btn("fa5s.edit", "Sua", _BTN_EDIT_STYLE)
                if is_active:
                    tog_style = _BTN_DEL_STYLE
                    tog_text = "Tat"
                    tog_icon = "fa5s.toggle-off"
                else:
                    tog_style = (
                        "QPushButton { background: #16a34a; color: white; border: none;"
                        " border-radius: 6px; padding: 5px 10px; font-size: 12px;"
                        " font-weight: 600; } QPushButton:hover { background: #15803d; }"
                    )
                    tog_text = "Bat"
                    tog_icon = "fa5s.toggle-on"
                toggle_btn = icon_btn(tog_icon, tog_text, tog_style)
                del_btn = icon_btn("fa5s.trash-alt", "Xoa", _BTN_DEL_STYLE)

                edit_btn.clicked.connect(lambda _=False, item=rule: self.edit_fee_rule(item))
                toggle_btn.clicked.connect(lambda _=False, item=rule: self.toggle_fee_rule(item))
                del_btn.clicked.connect(lambda _=False, item=rule: self.delete_fee_rule(item))

                a_row.addWidget(edit_btn); a_row.addWidget(toggle_btn)
                a_row.addStretch(); a_row.addWidget(del_btn)
                c.addLayout(a_row)

                grid.addWidget(f, index // 3, index % 3)

            if not rules:
                empty_lbl = label("Chua co bieu phi nao. Nhan '+ Them quy tac' de bat dau.", "muted")
                empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rules_layout.addWidget(empty_lbl)

            scroll.setWidget(grid_w); rules_layout.addWidget(scroll, 1)
            tabs.addTab(rules_tab, "💰  Quy tac phi")

            # Tab 2: Fee Calculator
            from PySide6.QtWidgets import QDateTimeEdit as _DTE
            from PySide6.QtCore import QDateTime as _QDT
            calc_tab = QWidget(); calc_layout = QVBoxLayout(calc_tab)
            calc_layout.setContentsMargins(20, 20, 20, 20); calc_layout.setSpacing(14)
            calc_layout.addWidget(label("Tinh phi thu", bold=True, style="font-size:18px;"))
            calc_layout.addWidget(label("Kiem tra so tien phai tra theo cau hinh bieu phi.", "muted"))

            sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet("color: #e2e8f0;"); calc_layout.addWidget(sep2)

            cg = QGridLayout(); cg.setSpacing(12)
            cg.addWidget(label("Loai xe", "muted"), 0, 0)
            calc_vehicle = QComboBox(); self.fill_vehicle_combo(calc_vehicle)
            cg.addWidget(calc_vehicle, 1, 0)

            cg.addWidget(label("Gio vao", "muted"), 0, 1)
            dt_in = _DTE(_QDT.currentDateTime().addSecs(-3600))
            dt_in.setDisplayFormat("dd/MM/yyyy HH:mm"); dt_in.setCalendarPopup(True)
            cg.addWidget(dt_in, 1, 1)

            cg.addWidget(label("Gio ra", "muted"), 0, 2)
            dt_out = _DTE(_QDT.currentDateTime())
            dt_out.setDisplayFormat("dd/MM/yyyy HH:mm"); dt_out.setCalendarPopup(True)
            cg.addWidget(dt_out, 1, 2)

            calc_btn2 = icon_btn("fa5s.calculator", "Tinh phi", _BTN_EDIT_STYLE)
            cg.addWidget(calc_btn2, 1, 3)
            calc_layout.addLayout(cg)

            result_frame = QFrame()
            result_frame.setStyleSheet(
                "background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px;"
            )
            result_vbox = QVBoxLayout(result_frame)
            result_detail = QLabel("")
            result_detail.setWordWrap(True)
            result_detail.setStyleSheet("color:#1e293b; font-size:13px; padding:8px;")
            result_vbox.addWidget(result_detail)
            calc_layout.addWidget(result_frame)
            result_frame.setVisible(False)

            def do_calc():
                try:
                    from pmql.domain.services.fee_calculator import FeeCalculator as _FC
                    v_code = calc_vehicle.currentData()
                    all_rules = asyncio.run(_fee_rules(settings))
                    active_rules = [r for r in all_rules if r.is_active and r.vehicle_type == v_code]
                    if not active_rules:
                        result_frame.setStyleSheet(
                            "background:#fef2f2; border:1px solid #fecaca; border-radius:8px;"
                        )
                        result_detail.setText(
                            "Khong tim thay quy tac phi nao dang ap dung cho loai xe nay."
                        )
                    else:
                        rule_c = active_rules[0]
                        entry = dt_in.dateTime().toPython()
                        exit_ = dt_out.dateTime().toPython()
                        minutes = max(0, int((exit_ - entry).total_seconds() / 60))
                        calc_obj = _FC(rule_c)
                        fee = calc_obj.calculate(entry, exit_)
                        hours, mins = divmod(minutes, 60)
                        result_frame.setStyleSheet(
                            "background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px;"
                        )
                        result_detail.setText(
                            f"<b>Thoi gian gui:</b> {hours} gio {mins} phut<br>"
                            f"<b>Quy tac ap dung:</b> {rule_c.name} "
                            f"({vehicle_names.get(rule_c.vehicle_type, rule_c.vehicle_type)})<br>"
                            f"<b>Gia/block:</b> {rule_c.price_per_block:,} d  |  "
                            f"<b>Block:</b> {rule_c.block_minutes} phut  |  "
                            f"<b>Mien phi:</b> {rule_c.free_minutes} phut<br>"
                            f"<span style='font-size:18px; color:#16a34a;'>"
                            f"<b>Tong phi: {fee:,} d</b></span>"
                        )
                    result_frame.setVisible(True)
                except Exception as exc:
                    result_detail.setText(f"Loi: {exc}")
                    result_frame.setVisible(True)

            calc_btn2.clicked.connect(do_calc)
            calc_layout.addStretch()
            tabs.addTab(calc_tab, "🧮  Tinh phi thu")

            # Tab 3: History
            from PySide6.QtGui import QColor as _QColor
            hist_tab = QWidget(); hist_layout = QVBoxLayout(hist_tab)
            hist_layout.setContentsMargins(12, 12, 12, 12)
            hist_layout.addWidget(label("Lich su cac quy tac phi", bold=True, style="font-size:16px;"))
            hist_layout.addWidget(label("Danh sach toan bo quy tac (dang ap dung va da tat).", "muted"))
            hist_tbl = self.make_table(
                ["Quy tac", "Loai xe", "Gia/block", "Block", "Mien phi", "Tran/ngay", "Trang thai"],
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
                        f"{sr.price_per_block:,} d",
                        f"{sr.block_minutes} phut",
                        f"{sr.free_minutes} phut",
                        f"{sr.day_max:,} d" if sr.day_max else "--",
                    )
                    for ci, val in enumerate(vals):
                        itm = QTableWidgetItem(val)
                        itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        hist_tbl.setItem(ri, ci, itm)
                    status_itm = QTableWidgetItem(
                        "Dang ap dung" if sr.is_active else "Da tat"
                    )
                    status_itm.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    status_itm.setForeground(
                        _QColor("#166534" if sr.is_active else "#94a3b8")
                    )
                    hist_tbl.setItem(ri, 6, status_itm)
            except Exception:
                pass
            hist_layout.addWidget(hist_tbl, 1)
            tabs.addTab(hist_tab, "🗓  Lich su")

            box.addWidget(tabs, 1)
            return page

        def toggle_fee_rule(self, rule) -> None:
            try:
                from pmql.infrastructure.persistence.sqlite.database import Database as _DB2
                from pmql.infrastructure.persistence.sqlite.repositories import SQLiteFeeRuleRepository as _FR2
                async def _do_toggle():
                    db = _DB2(settings.local_database_url)
                    async with db.session() as session:
                        repo = _FR2(session)
                        r = await repo.get_by_id(rule.id)
                        if r:
                            r.is_active = not r.is_active
                            await repo.update(r)
                    await db.dispose()
                asyncio.run(_do_toggle())
                self.reload_page("fees")
            except Exception as exc:
                QMessageBox.warning(self, "Loi", str(exc))

'''

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

# Find the fee_page block and replace it
start_marker = "        def fee_page(self) -> QWidget:\n"
end_marker = "\n        def subscriber_page(self) -> QWidget:"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print(f"MARKERS NOT FOUND: start={start_idx}, end={end_idx}")
else:
    new_content = content[:start_idx] + NEW_FEE_PAGE + content[end_idx + 1:]
    with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("DONE - fee_page replaced successfully")
