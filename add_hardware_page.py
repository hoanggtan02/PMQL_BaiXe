import sys

with open("src/pmql/ui/app.py", encoding="utf-8") as f:
    content = f.read()

# ── 1. Add device repo helpers ────────────────────────────────────────────────
DEVICE_HELPERS = """
async def _list_devices(settings: Settings):
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    from sqlalchemy import select
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            rows = (await session.execute(select(DeviceModel).where(DeviceModel.branch_id == settings.branch_id))).scalars().all()
            return list(rows)
    finally:
        await db.dispose()

async def _save_device(settings: Settings, device_type: str, protocol: str, lane_id: str, name: str):
    import uuid
    from datetime import datetime
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            dev = DeviceModel(
                id=str(uuid.uuid4()),
                branch_id=settings.branch_id,
                name=name or f"{device_type} - {protocol}",
                device_type=device_type,
                connection_string=f"protocol={protocol};lane={lane_id}",
                is_online=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                sync_version=1
            )
            session.add(dev)
    finally:
        await db.dispose()

async def _delete_device(settings: Settings, device_id: str):
    from pmql.infrastructure.persistence.sqlite.models import DeviceModel
    db = Database(settings.local_database_url)
    try:
        async with db.session() as session:
            dev = await session.get(DeviceModel, device_id)
            if dev:
                await session.delete(dev)
    finally:
        await db.dispose()
"""

if "_list_devices" not in content:
    content += DEVICE_HELPERS

# ── 2. Add hardware_page method ────────────────────────────────────────────────
HARDWARE_PAGE = """        def hardware_page(self) -> QWidget:
            page, box = self.page()
            title = label("Kết nối & Cài đặt thiết bị thật", bold=True)
            title.setStyleSheet("font-size:24px;")
            box.addWidget(title)

            # Device type definitions
            DEVICE_TYPES = [
                ("rfid",    "🪪",  "Đầu đọc thẻ",  "RFID / NFC",        "#3b82f6",
                 [("TCP Socket","Kết nối IP trực tiếp"), ("Wiegand","Wiegand 26/34 bit"), ("RS485 Serial","USB-RS485 adapter")]),
                ("camera",  "📷", "Camera ANPR",  "Nhận dạng biển số",  "#f59e0b",
                 [("RTSP Stream","IP Camera qua mạng LAN"), ("HTTP API","SDK HTTP Dahua/Hikvision"), ("USB Camera","Camera USB/Webcam")]),
                ("finger",  "👆", "Vân tay",       "Nhận dạng sinh trắc","#a855f7",
                 [("SDK TCP","ZKTeco qua mạng"), ("RS485/UART","Module vân tay serial"), ("USB Module","Module USB vân tay")]),
                ("barrier", "🚧", "Barrier",       "Barie tự động",       "#22c55e",
                 [("RS485 Modbus","Barrier qua RS485"), ("RS232 Serial","Cổng serial COM"), ("Relay GPIO","Relay board / Arduino"), ("TCP IP","Barrier có IP")]),
            ]

            import asyncio

            # ── Right panel ─────────────────────────────────────────────────
            right_w = QWidget(); right_w.setFixedWidth(280)
            right_col = QVBoxLayout(right_w); right_col.setContentsMargins(0,0,0,0); right_col.setSpacing(12)

            def section_box(icon, title_text, color):
                f = QFrame(); f.setStyleSheet("QFrame { background: white; border: none; border-radius: 8px; }")
                v = QVBoxLayout(f); v.setContentsMargins(14,12,14,12); v.setSpacing(6)
                h = QHBoxLayout()
                ico_lbl = label(icon); ico_lbl.setStyleSheet(f"background:{color}20;color:{color};border:none;border-radius:4px;padding:3px 7px;")
                h.addWidget(ico_lbl); t = label(title_text, bold=True); t.setStyleSheet("border:none;"); h.addWidget(t); h.addStretch()
                v.addLayout(h); return f, v

            sdk_f, sdk_v = section_box("📦", "SDK & Thư viện hỗ trợ", "#f97316")
            for line in ["• SDK TCP (ZKTeco, Hikvision, Dahua)","• Thư viện: python-aiougent, evdev",""]:
                l = label(line); l.setStyleSheet("color:#475569;font-size:11px;border:none;"); l.setWordWrap(True); sdk_v.addWidget(l)
            for tag, items in [("📷 Camera ANPR", ["• RTSP stream → OpenCV → AI model","• HTTP API (Dahua, Hikvision SDK)","• ONVIF → RTSP capture"]),
                                ("👆 Vân tay", ["• ZKTeco SDK (hỗ trợ Python)","• UART/RS485 → USB adapter","• FP template lưu trong DB"]),
                                ("🚧 Barrier / Barie", ["• RS485 Modbus RTU","• RS232 Serial protocol","• Relay output (GPIO / USB relay)"])]:
                h2 = label(tag, bold=True); h2.setStyleSheet("color:#1e293b;font-size:12px;border:none;margin-top:6px;"); sdk_v.addWidget(h2)
                for it in items:
                    l2 = label(it); l2.setStyleSheet("color:#475569;font-size:11px;border:none;"); sdk_v.addWidget(l2)
            right_col.addWidget(sdk_f)

            # Connected devices panel
            conn_f, conn_v = section_box("🔌", "Thiết bị đang kết nối", "#22c55e")
            refresh_btn = QPushButton("⟳"); refresh_btn.setFixedSize(28,28)
            refresh_btn.setStyleSheet("border:none;border-radius:14px;background:#f1f5f9;font-weight:bold;padding:0;")
            conn_f.layout().itemAt(0).layout().addWidget(refresh_btn)

            devices_list_lbl = label("", "muted"); devices_list_lbl.setWordWrap(True)

            def refresh_devices():
                try:
                    devs = asyncio.run(_list_devices(settings))
                    if devs:
                        lines = []
                        for d in devs:
                            icon_map = {"rfid":"🪪","camera":"📷","finger":"👆","barrier":"🚧"}
                            ico = icon_map.get(d.device_type, "📡")
                            lines.append(f"{ico} {d.name}")
                        devices_list_lbl.setText("\\n".join(lines))
                    else:
                        devices_list_lbl.setText("Chưa có thiết bị nào kết nối\\nHoặc kết nối TCP qua cổng 9001")
                except: devices_list_lbl.setText("Chưa có thiết bị nào kết nối")

            refresh_devices()
            refresh_btn.clicked.connect(refresh_devices)
            conn_v.addWidget(devices_list_lbl)

            check_btn = QPushButton("⟳ Kiểm tra lại")
            check_btn.setStyleSheet("background:white;border:1px solid #cbd5e1;border-radius:6px;padding:6px 14px;color:#475569;font-weight:600;")
            check_btn.clicked.connect(refresh_devices)
            conn_v.addWidget(check_btn)

            note = label("ℹ Chi hiển thị thiết bị đang kết nối TCP thực tế vào cổng 9001")
            note.setStyleSheet("color:#94a3b8;font-size:11px;border:none;")
            note.setWordWrap(True)
            conn_v.addWidget(note)
            right_col.addWidget(conn_f)
            right_col.addStretch()

            # ── Left panel ──────────────────────────────────────────────────
            left_w = QWidget()
            left_col = QVBoxLayout(left_w); left_col.setContentsMargins(0,0,0,0); left_col.setSpacing(16)

            selected_type = [None]     # mutable ref
            selected_proto = [None]
            device_card_refs = {}
            proto_btn_refs = []

            # Step section helper
            def step_frame(num, title_text):
                f = QFrame(); f.setStyleSheet("QFrame { background: white; border: none; border-radius: 8px; }")
                v = QVBoxLayout(f); v.setContentsMargins(16,14,16,14); v.setSpacing(10)
                h = QHBoxLayout(); h.setSpacing(10)
                badge = label(str(num), bold=True)
                badge.setFixedSize(28,28)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet("background:#f97316;color:white;border-radius:14px;border:none;font-size:13px;font-weight:700;")
                h.addWidget(badge)
                t = label(title_text, bold=True); t.setStyleSheet("font-size:14px;border:none;"); h.addWidget(t); h.addStretch()
                v.addLayout(h)
                return f, v

            # ── Step 1 — Chọn loại thiết bị ─────────────────────────────
            s1_frame, s1_v = step_frame(1, "Chọn loại thiết bị cần kết nối")
            card_row = QHBoxLayout(); card_row.setSpacing(12)

            proto_section_frame_ref = [None]
            proto_label_ref = [None]
            proto_btn_row_ref = [None]

            def make_device_card(key, icon, name, sub, color, protos):
                card = QFrame()
                card.setObjectName(f"devcard_{key}")
                card.setFixedWidth(150); card.setFixedHeight(120)
                card.setCursor(Qt.CursorShape.PointingHandCursor)
                card.setStyleSheet("QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 10px; }")
                v = QVBoxLayout(card); v.setContentsMargins(10,10,10,10); v.setAlignment(Qt.AlignmentFlag.AlignCenter)

                ico_lbl = label(icon); ico_lbl.setStyleSheet(f"font-size:28px;border:none;background:{color}15;border-radius:8px;padding:6px 10px;")
                ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                n_lbl = label(name, bold=True); n_lbl.setStyleSheet("border:none;font-size:12px;"); n_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                s_lbl = label(sub, "muted"); s_lbl.setStyleSheet("color:#94a3b8;font-size:11px;border:none;"); s_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                v.addWidget(ico_lbl); v.addWidget(n_lbl); v.addWidget(s_lbl)

                def on_click(_, k=key, c=color, ps=protos, nm=name):
                    selected_type[0] = k; selected_proto[0] = None
                    for ck, cf in device_card_refs.items():
                        if ck == k:
                            cf.setStyleSheet(f"QFrame {{ background: {c}10; border: 2px solid {c}; border-radius: 10px; }}")
                        else:
                            cf.setStyleSheet("QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 10px; }")
                    # Update protocol section
                    if proto_label_ref[0]: proto_label_ref[0].setText(nm)
                    if proto_btn_row_ref[0]:
                        layout = proto_btn_row_ref[0]
                        while layout.count(): layout.takeAt(0).widget().deleteLater() if layout.itemAt(0) and layout.itemAt(0).widget() else layout.takeAt(0)
                        proto_btn_refs.clear()
                        for p_name, p_sub in ps:
                            pb = QPushButton(f"{p_name}\\n{p_sub}")
                            pb.setCheckable(True)
                            pb.setStyleSheet("QPushButton{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:6px 14px;font-size:12px;color:#475569;}"
                                             "QPushButton:checked{background:#fff7ed;border:2px solid #f97316;color:#ea580c;font-weight:700;}")
                            def on_proto(chk, pn=p_name, pb_ref=pb):
                                selected_proto[0] = pn
                                for rb in proto_btn_refs:
                                    if rb is not pb_ref: rb.setChecked(False)
                            pb.clicked.connect(on_proto)
                            layout.addWidget(pb)
                            proto_btn_refs.append(pb)
                        layout.addStretch()

                class ClickFrame(type(card)):
                    def mousePressEvent(self, ev): on_click(True)
                card.__class__ = ClickFrame
                device_card_refs[key] = card
                return card

            for key, icon, name, sub, color, protos in DEVICE_TYPES:
                card_row.addWidget(make_device_card(key, icon, name, sub, color, protos))
            card_row.addStretch()
            s1_v.addLayout(card_row)
            left_col.addWidget(s1_frame)

            # ── Step 2 — Chọn giao thức ──────────────────────────────────
            s2_frame, s2_v = step_frame(2, "Chọn giao thức kết nối")
            s2_h = s2_frame.layout().itemAt(0).layout()
            proto_lbl = label("—", "muted"); proto_lbl.setStyleSheet("color:#94a3b8;font-size:12px;border:none;")
            s2_h.addWidget(proto_lbl); proto_label_ref[0] = proto_lbl

            note2 = label("Chọn giao thức phù hợp với thiết bị của bạn:"); note2.setStyleSheet("color:#64748b;font-size:12px;border:none;")
            s2_v.addWidget(note2)
            proto_row = QHBoxLayout(); proto_row.setSpacing(10)
            proto_btn_row_ref[0] = proto_row
            proto_row.addStretch()
            s2_v.addLayout(proto_row)
            left_col.addWidget(s2_frame)

            # ── Step 3 — Gán làn xe ──────────────────────────────────────
            s3_frame, s3_v = step_frame(3, "Gán thiết bị vào làn xe")
            s3_grid = QGridLayout(); s3_grid.setSpacing(16)

            s3_grid.addWidget(label("Chọn làn xe", "muted"), 0, 0)
            lane_combo = QComboBox(); lane_combo.addItem("— Chọn làn —")
            try:
                for ln in asyncio.run(_lanes(settings)): lane_combo.addItem(ln.name, ln.id)
            except: pass
            s3_grid.addWidget(lane_combo, 1, 0)

            s3_grid.addWidget(label("Tên thiết bị (tùy chọn)", "muted"), 0, 1)
            name_edit = QLineEdit(); name_edit.setPlaceholderText("VD: Camera làn 1 vào")
            s3_grid.addWidget(name_edit, 1, 1)
            s3_v.addLayout(s3_grid)
            left_col.addWidget(s3_frame)

            # ── Step 4 — Test & Lưu ─────────────────────────────────────
            s4_frame, s4_v = step_frame(4, "Kiểm tra kết nối và lưu cấu hình")
            s4_h = QHBoxLayout(); s4_h.setSpacing(12)

            test_btn = QPushButton("⚡ Test kết nối")
            test_btn.setStyleSheet("background:white;border:1px solid #3b82f6;color:#3b82f6;border-radius:6px;padding:8px 18px;font-weight:700;")
            save_btn = QPushButton("💾 Lưu thiết bị")
            save_btn.setStyleSheet("background:#f97316;color:white;border:none;border-radius:6px;padding:8px 18px;font-weight:700;")

            status_lbl = label(""); status_lbl.setStyleSheet("border:none;")

            def on_test():
                if not selected_type[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn loại thiết bị trước."); return
                if not selected_proto[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn giao thức kết nối."); return
                status_lbl.setText("⏳ Đang kiểm tra..."); status_lbl.setStyleSheet("color:#f59e0b;border:none;")
                # Simulate test result (mock)
                status_lbl.setText("✅ Mô phỏng thành công (Mock mode)"); status_lbl.setStyleSheet("color:#16a34a;border:none;")

            def on_save():
                if not selected_type[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn loại thiết bị."); return
                if not selected_proto[0]:
                    QMessageBox.warning(page, "Chưa chọn", "Vui lòng chọn giao thức kết nối."); return
                lane_id = lane_combo.currentData() or ""
                dev_name = name_edit.text().strip()
                try:
                    asyncio.run(_save_device(settings, selected_type[0], selected_proto[0], lane_id, dev_name))
                    QMessageBox.information(page, "Đã lưu", f"Thiết bị đã được lưu thành công!")
                    refresh_devices()
                except Exception as e:
                    QMessageBox.critical(page, "Lỗi", str(e))

            test_btn.clicked.connect(on_test)
            save_btn.clicked.connect(on_save)
            s4_h.addWidget(test_btn); s4_h.addWidget(save_btn); s4_h.addWidget(status_lbl); s4_h.addStretch()
            s4_v.addLayout(s4_h)
            left_col.addWidget(s4_frame)

            # ── Resources section ────────────────────────────────────────
            res_f = QFrame(); res_f.setStyleSheet("QFrame { background: white; border: none; border-radius: 8px; }")
            res_v = QVBoxLayout(res_f); res_v.setContentsMargins(16,14,16,14); res_v.setSpacing(12)
            res_h0 = QHBoxLayout()
            res_ico = label("📦"); res_ico.setStyleSheet("background:#f97316;color:white;border:none;border-radius:4px;padding:3px 7px;font-size:14px;")
            res_h0.addWidget(res_ico); t2 = label("Tài nguyên & Driver mẫu", bold=True); t2.setStyleSheet("border:none;"); res_h0.addWidget(t2); res_h0.addStretch()
            res_v.addLayout(res_h0)
            cards_h = QHBoxLayout(); cards_h.setSpacing(12)
            for icon, title_r, sub_r, color_r in [
                ("🐍","Driver Python TCP","Tải liệu PDF - client TCP","#3b82f6"),
                ("🔷","Arduino / ESP32","Tải liệu PDF - RFID TCP","#22c55e"),
                ("🍓","Raspberry Pi","Tải liệu PDF - Pi + Camera","#ef4444"),
                ("📄","Tài liệu giao thức","PDF - TCP Protocol full","#f97316"),
            ]:
                rc = QFrame(); rc.setStyleSheet("QFrame{background:#f8fafc;border-radius:8px;border:none;}")
                rv = QVBoxLayout(rc); rv.setContentsMargins(12,12,12,12); rv.setSpacing(6)
                ri = label(icon); ri.setStyleSheet(f"font-size:22px;background:{color_r}15;border-radius:6px;padding:4px 8px;border:none;"); ri.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rv.addWidget(ri)
                rv.addWidget(label(title_r, bold=True))
                rv.addWidget(label(sub_r, "muted"))
                rb = QPushButton("📥 Xuất PDF")
                rb.setStyleSheet(f"background:{color_r};color:white;border:none;border-radius:4px;padding:5px;font-weight:600;font-size:11px;")
                rv.addWidget(rb); cards_h.addWidget(rc)
            res_v.addLayout(cards_h); left_col.addWidget(res_f)
            left_col.addStretch()

            # ── Assemble main layout ─────────────────────────────────────
            main_h = QHBoxLayout(); main_h.setSpacing(20)
            scroll_w = QScrollArea(); scroll_w.setWidgetResizable(True); scroll_w.setFrameShape(QFrame.Shape.NoFrame)
            scroll_w.setWidget(left_w); main_h.addWidget(scroll_w, 1); main_h.addWidget(right_w)
            content_w = QWidget(); content_w.setLayout(main_h)
            box.addWidget(content_w, 1)
            return page

"""

target = "        def accounts_page(self) -> QWidget:"
if "def hardware_page" not in content:
    content = content.replace(target, HARDWARE_PAGE + "\n" + target)

# ── 3. Register hardware_page in factories + sidebar ─────────────────────────
content = content.replace(
    '"settings": self.settings_page}',
    '"settings": self.settings_page, "hardware": self.hardware_page}'
)
content = content.replace(
    '("HỆ THỐNG", [("accounts", "♙  Tài khoản & phân quyền"), ("settings", "⚙  Cài đặt")])',
    '("HỆ THỐNG", [("accounts", "♙  Tài khoản & phân quyền"), ("settings", "⚙  Cài đặt"), ("hardware", "🔌  Kết nối thiết bị")])'
)
content = content.replace(
    '"settings":"Cài đặt hệ thống"}',
    '"settings":"Cài đặt hệ thống", "hardware":"Kết nối & Cài đặt thiết bị thật"}'
)

with open("src/pmql/ui/app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("hardware_page added successfully!")
