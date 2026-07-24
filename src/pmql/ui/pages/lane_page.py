from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

# Direction display map
_DIR_MAP = {
    "IN":            ("↗ Xe vào",   "#dcfce7", "#16a34a"),
    "OUT":           ("↙ Xe ra",    "#fee2e2", "#dc2626"),
    "BIDIRECTIONAL": ("↔ Hai chiều","#e0e7ff", "#4f46e5"),
}
_DIR_LABEL = {"IN": "Xe vào ↗", "OUT": "Xe ra ↙", "BIDIRECTIONAL": "Hai chiều ↔"}

# Status config: key → (text, badge_bg, badge_color, card_bg, card_border)
_STAT = {
    "active":   ("● Hoạt động", "#dcfce7", "#16a34a"),
    "inactive": ("■ Tắt",       "#fee2e2", "#dc2626"),
    "maintain": ("🔧 Bảo trì",  "#fff7ed", "#d97706"),
}

def _lane_status_key(lane) -> str:
    return "active" if lane.is_active else "inactive"


class LanePageMixin:
    def lane_page(self) -> QWidget:
        page, box = self.page(); box.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        self.lane_count_lbl = label("| 0 làn hoạt động", "muted")
        header.addWidget(self.lane_count_lbl); header.addStretch()
        add = QPushButton("+ Thêm làn xe"); add.setObjectName("primary")
        add.setStyleSheet("background:#f97316; color:white; border:none; border-radius:6px; padding:8px 16px; font-weight:bold;")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(self.add_lane)
        header.addWidget(add); box.addLayout(header)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        self.lane_container = QWidget()
        self.lane_grid = QGridLayout(self.lane_container)
        self.lane_grid.setSpacing(16)
        self.lane_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.lane_container); box.addWidget(scroll, 1)
        self.load_lanes(); return page

    # ── Load & render ────────────────────────────────────────────────
    def load_lanes(self) -> None:
        if not hasattr(self, "lane_grid"): return
        while self.lane_grid.count():
            w = self.lane_grid.takeAt(0)
            if w.widget(): w.widget().deleteLater()

        try: lanes = asyncio.run(_lanes(self.settings))
        except Exception as e: show_toast(self, str(e), "error"); return

        active = sum(1 for l in lanes if l.is_active)
        self.lane_count_lbl.setText(f"| {active}/{len(lanes)} làn hoạt động")

        if not lanes:
            e = label("Chưa có làn nào — bấm '+ Thêm làn xe' để cấu hình", "muted")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lane_grid.addWidget(e, 0, 0, 1, 2); return

        for idx, lane in enumerate(lanes):
            sk = _lane_status_key(lane)
            card = QFrame(); card.setObjectName("lnCard")
            if sk == "active":
                card.setStyleSheet("QFrame#lnCard{background:white; border:none; border-radius:8px;}")
            elif sk == "inactive":
                card.setStyleSheet("QFrame#lnCard{background:#fff5f5; border:1px solid #fecaca; border-radius:8px;}")
            else:
                card.setStyleSheet("QFrame#lnCard{background:#fffbeb; border:1px solid #fde68a; border-radius:8px;}")

            cb = QVBoxLayout(card); cb.setContentsMargins(20, 18, 20, 18); cb.setSpacing(10)

            # Name + count
            top = QHBoxLayout()
            nm_color = "#0f172a" if sk == "active" else ("#dc2626" if sk == "inactive" else "#d97706")
            top.addWidget(label(lane.name, style=f"font-size:16px; font-weight:bold; color:{nm_color};"))
            top.addStretch()
            vc = QVBoxLayout(); vc.setSpacing(0)
            vc.addWidget(label("0", bold=True, style="color:#f59e0b; font-size:18px;"), alignment=Qt.AlignmentFlag.AlignHCenter)
            vc.addWidget(label("Xe đang gửi", style="font-size:10px; color:#94a3b8;"), alignment=Qt.AlignmentFlag.AlignHCenter)
            top.addLayout(vc); cb.addLayout(top)

            # Tags
            tr = QHBoxLayout(); tr.setSpacing(8)
            dt, dbg, dc = _DIR_MAP.get(lane.direction, ("?", "#f1f5f9", "#64748b"))
            tr.addWidget(label(dt, style=f"background:{dbg}; color:{dc}; border-radius:12px; padding:3px 10px; font-size:11px; font-weight:600;"))
            st, sbg, sc = _STAT[sk]
            tr.addWidget(label(st, style=f"background:{sbg}; color:{sc}; border-radius:12px; padding:3px 10px; font-size:11px; font-weight:600;"))
            tr.addStretch(); cb.addLayout(tr)

            # Devices
            cb.addWidget(label("THIẾT BỊ LẮP ĐẶT", style="font-size:10px; font-weight:700; color:#94a3b8; letter-spacing:1px;"))
            dr = QHBoxLayout(); dr.setSpacing(6)
            ds = "background:#f0fdf4; color:#16a34a; border:none; border-radius:5px; padding:3px 8px; font-size:11px;"
            nd = "background:#f1f5f9; color:#94a3b8; border:none; border-radius:5px; padding:3px 8px; font-size:11px;"
            has = False
            if lane.rfid_device_id: dr.addWidget(label("💳 Thẻ RFID", style=ds)); has = True
            if lane.camera_source: dr.addWidget(label("📷 Camera", style=ds)); has = True
            if lane.barrier_device_id: dr.addWidget(label("🚧 Barrier", style=ds)); has = True
            if not has: dr.addWidget(label("Chưa gắn thiết bị", style=nd))
            dr.addStretch(); cb.addLayout(dr)

            # Separator + actions
            sp = QFrame(); sp.setFrameShape(QFrame.Shape.HLine); sp.setStyleSheet("border:none; border-top:1px solid #f1f5f9;")
            cb.addWidget(sp)
            ar = QHBoxLayout(); ar.setSpacing(8)
            eb = QPushButton("✏ Sửa cấu hình")
            eb.setStyleSheet("QPushButton{background:white; border:1px solid #bfdbfe; color:#2563eb; border-radius:6px; padding:6px 12px; font-weight:600; font-size:12px;} QPushButton:hover{background:#eff6ff;}")
            eb.setCursor(Qt.CursorShape.PointingHandCursor)
            eb.clicked.connect(lambda _=False, l=lane: self.edit_lane(l))
            db = QPushButton("✕ Xóa")
            db.setStyleSheet("QPushButton{background:white; border:1px solid #fecaca; color:#dc2626; border-radius:6px; padding:6px 12px; font-weight:600; font-size:12px;} QPushButton:hover{background:#fef2f2;}")
            db.setCursor(Qt.CursorShape.PointingHandCursor)
            db.clicked.connect(lambda _=False, l=lane: self.delete_lane(l))
            ar.addWidget(eb, 1); ar.addWidget(db); cb.addLayout(ar)

            self.lane_grid.addWidget(card, idx // 2, idx % 2)

    # ── Edit / Add Modal ─────────────────────────────────────────────
    def show_lane_modal(self, lane=None):
        title = "Thêm làn xe" if not lane else "Sửa cấu hình làn"
        dialog, content, footer = modal_shell(self, title, 540)

        content.addWidget(label("Tên làn *", style="font-size:12px; font-weight:600; color:#64748b;"))
        name_edit = QLineEdit(lane.name if lane else "")
        name_edit.setPlaceholderText("Ví dụ: Làn vào 1, Làn ra A …")
        content.addWidget(name_edit)
        content.addWidget(label("Tên hiển thị trên màn hình vận hành", style="font-size:11px; color:#94a3b8;"))
        content.addSpacing(12)

        rw = QWidget(); rl = QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(16)
        # Direction
        dw = QWidget(); dl = QVBoxLayout(dw); dl.setContentsMargins(0,0,0,0); dl.setSpacing(6)
        dl.addWidget(label("Chiều xe", style="font-size:12px; font-weight:600; color:#64748b;"))
        direction = QComboBox()
        direction.addItem("↗ Xe vào (IN)", "IN")
        direction.addItem("↙ Xe ra (OUT)", "OUT")
        direction.addItem("↔ Hai chiều", "BIDIRECTIONAL")
        dl.addWidget(direction)
        # Status
        sw = QWidget(); sl = QVBoxLayout(sw); sl.setContentsMargins(0,0,0,0); sl.setSpacing(6)
        sl.addWidget(label("Trạng thái", style="font-size:12px; font-weight:600; color:#64748b;"))
        status = QComboBox()

        def _make_icon(color_hex: str, symbol: str) -> QIcon:
            pm = QPixmap(16, 16); pm.fill(QColor("transparent"))
            p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            c = QColor(color_hex)
            if symbol == "check":
                pen = QPen(c, 2.5); p.setPen(pen)
                p.drawLine(3, 8, 6, 12)
                p.drawLine(6, 12, 13, 4)
            elif symbol == "x":
                pen = QPen(c, 2.5); p.setPen(pen)
                p.drawLine(3, 3, 13, 13)
                p.drawLine(13, 3, 3, 13)
            elif symbol == "wrench":
                # Dùng emoji 🔧 trực tiếp
                p.setPen(QColor(color_hex))
                f = p.font(); f.setPixelSize(13); p.setFont(f)
                p.drawText(QRect(0, 0, 16, 16), Qt.AlignmentFlag.AlignCenter, "🔧")
            p.end()
            return QIcon(pm)

        status.addItem(_make_icon("#16a34a", "check"),   "Hoạt động", "active")
        status.addItem(_make_icon("#dc2626", "x"),       "Tắt",       "inactive")
        status.addItem(_make_icon("#d97706", "wrench"),  "Bảo trì",   "maintain")
        status.setIconSize(QSize(16, 16))
        sl.addWidget(status)
        rl.addWidget(dw, 1); rl.addWidget(sw, 1); content.addWidget(rw)
        content.addSpacing(12)
        content.addWidget(label("Thiết bị có thể gán ở mục Kết nối thiết bị sau khi lưu.", style="font-size:11px; color:#94a3b8;"))

        if lane:
            direction.setCurrentIndex(max(0, direction.findData(lane.direction)))
            cur = _lane_status_key(lane)
            status.setCurrentIndex(max(0, status.findData(cur)))

        cancel = QPushButton("Hủy")
        cancel.setStyleSheet("QPushButton{background:#f1f5f9; color:#475569; border:none; border-radius:6px; padding:8px 20px; font-weight:600;} QPushButton:hover{background:#e2e8f0;}")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        save = QPushButton("💾 Lưu cấu hình")
        save.setStyleSheet("QPushButton{background:#f97316; color:white; border:none; border-radius:6px; padding:8px 20px; font-weight:700;} QPushButton:hover{background:#ea6c0a;}")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save)
        cancel.clicked.connect(dialog.reject)

        camera  = lane.camera_source     if lane else "cam1"
        rfid    = lane.rfid_device_id    if lane else "rfid1"
        barrier = lane.barrier_device_id if lane else "bar1"

        stat_lbl = {"active": "Hoạt động", "inactive": "Tắt", "maintain": "Bảo trì"}

        def do_save():
            nn = name_edit.text().strip()
            if not nn: show_toast(dialog, "Tên làn không được để trống", "error"); return
            nd = direction.currentData()
            ns = status.currentData()
            na = ns == "active"

            if lane:
                old_s = _lane_status_key(lane)
                # Build rows: (field, old_display, new_display, changed?)
                rows = []
                rows.append(("Tên làn",    lane.name,                 nn,                          nn != lane.name))
                rows.append(("Chiều xe",   _DIR_LABEL.get(lane.direction, lane.direction),
                                           _DIR_LABEL.get(nd, nd),                                 nd != lane.direction))
                rows.append(("Trạng thái", stat_lbl[old_s],           stat_lbl[ns],                ns != old_s))
                if not self._lane_confirm(dialog, rows): return

            try:
                if lane:
                    asyncio.run(_update_lane(self.settings, lane.id, nn, nd, camera, rfid, barrier, na))
                    msg = "Cập nhật làn xe thành công!"
                else:
                    asyncio.run(_create_lane(self.settings, nn, nd, camera, rfid, barrier))
                    msg = "Thêm làn xe thành công!"
                self.load_lanes()
                if hasattr(self, 'reload_page'): self.reload_page('operations')
                dialog.accept(); show_toast(self, msg, "success")
            except Exception as exc: show_toast(dialog, str(exc), "error")

        save.clicked.connect(do_save); dialog.exec()

    # ── Confirm dialog (y chang hình mẫu) ────────────────────────────
    def _lane_confirm(self, parent_dlg, rows: list) -> bool:
        """rows = [(field, old_val, new_val, changed_bool), ...]"""
        dlg = QDialog(self); dlg.setModal(True); dlg.setFixedWidth(480)
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet("QDialog{background:white; border-radius:12px; border:1px solid #e2e8f0;} QLabel{background:transparent;}")

        root = QVBoxLayout(dlg); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── HEADER ───────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24, 18, 24, 14)
        warn_icon = QLabel("⚠"); warn_icon.setStyleSheet("font-size:20px; color:#d97706;")
        ttl = QLabel("Xác nhận lưu thay đổi"); ttl.setStyleSheet("font-size:16px; font-weight:700; color:#1e293b; margin-left:8px;")
        xb = QPushButton("✕"); xb.setFixedSize(28, 28)
        xb.setStyleSheet("QPushButton{background:transparent; border:none; color:#94a3b8; font-size:16px;} QPushButton:hover{color:#475569;}")
        xb.setCursor(Qt.CursorShape.PointingHandCursor); xb.clicked.connect(dlg.reject)
        hl.addWidget(warn_icon); hl.addWidget(ttl, 1); hl.addWidget(xb)
        root.addWidget(hdr)

        # ── BODY ─────────────────────────────────────────────────────
        body = QWidget(); body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(24, 4, 24, 16); bl.setSpacing(14)

        desc = QLabel("Kiểm tra lại thay đổi trước khi lưu. Thao tác sẽ được ghi vào lịch sử backup.")
        desc.setWordWrap(True); desc.setStyleSheet("color:#64748b; font-size:13px;")
        bl.addWidget(desc)

        # Diff box
        df = QFrame(); df.setObjectName("diffBox")
        df.setStyleSheet("QFrame#diffBox{background:#fffbeb; border:1px solid #fde68a; border-radius:8px;}")
        dfl = QVBoxLayout(df); dfl.setContentsMargins(16, 14, 16, 14); dfl.setSpacing(0)

        # Title row
        dtitle = QLabel("✏ Cập nhật cấu hình làn")
        dtitle.setStyleSheet("color:#b45309; font-weight:700; font-size:13px;")
        dfl.addWidget(dtitle)
        dfl.addSpacing(10)

        # Separator
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background:#fde68a;")
        dfl.addWidget(sep)
        dfl.addSpacing(10)

        # Field rows
        for i, (field, old_v, new_v, changed) in enumerate(rows):
            rw = QWidget(); rw.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(rw); rl.setContentsMargins(0, 4, 0, 4); rl.setSpacing(0)

            # Field label — fixed width
            fl = QLabel(field); fl.setFixedWidth(90)
            fl.setStyleSheet("color:#64748b; font-size:12px;")
            rl.addWidget(fl)

            if changed:
                ol = QLabel(old_v); ol.setStyleSheet("color:#dc2626; font-size:12px; font-weight:600;")
                rl.addWidget(ol)
                rl.addSpacing(8)
                ar = QLabel("→"); ar.setStyleSheet("color:#94a3b8; font-size:12px;")
                rl.addWidget(ar)
                rl.addSpacing(8)
                nl = QLabel(new_v); nl.setStyleSheet("color:#1e293b; font-size:12px; font-weight:700;")
                rl.addWidget(nl)
            else:
                val = QLabel(f"{old_v} (không đổi)")
                val.setStyleSheet("color:#94a3b8; font-size:12px;")
                rl.addWidget(val)

            rl.addStretch()
            dfl.addWidget(rw)

        bl.addWidget(df)
        root.addWidget(body)

        # ── FOOTER ───────────────────────────────────────────────────
        ftr = QWidget()
        ftr.setStyleSheet("background:#f8fafc; border-top:1px solid #e2e8f0;")
        ffl = QHBoxLayout(ftr); ffl.setContentsMargins(24, 14, 24, 14); ffl.setSpacing(10)
        ffl.addStretch()

        cb = QPushButton("✕ Hủy")
        cb.setStyleSheet("QPushButton{background:#475569; color:white; border:none; border-radius:6px; padding:8px 22px; font-weight:600; font-size:13px;} QPushButton:hover{background:#334155;}")
        cb.setCursor(Qt.CursorShape.PointingHandCursor); cb.clicked.connect(dlg.reject)
        fb = QPushButton("✓ Xác nhận lưu")
        fb.setStyleSheet("QPushButton{background:#16a34a; color:white; border:none; border-radius:6px; padding:8px 22px; font-weight:700; font-size:13px;} QPushButton:hover{background:#15803d;}")
        fb.setCursor(Qt.CursorShape.PointingHandCursor); fb.clicked.connect(dlg.accept)
        ffl.addWidget(cb); ffl.addWidget(fb)
        root.addWidget(ftr)

        return dlg.exec() == QDialog.DialogCode.Accepted

    # ── CRUD ─────────────────────────────────────────────────────────
    def add_lane(self)  -> None: self.show_lane_modal()
    def edit_lane(self, lane) -> None: self.show_lane_modal(lane)

    def delete_lane(self, lane) -> None:
        if QMessageBox.question(self, "Xóa làn", f"Xóa làn '{lane.name}'?") != QMessageBox.StandardButton.Yes: return
        try:
            asyncio.run(_delete_lane(self.settings, lane.id))
            self.load_lanes()
            if hasattr(self, 'reload_page'): self.reload_page('operations')
            show_toast(self, "Xóa làn xe thành công!", "success")
        except Exception as exc: show_toast(self, str(exc), "error")
