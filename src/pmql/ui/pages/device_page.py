from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio

class DevicePageMixin:
    def hardware_page(self) -> QWidget:
        page, _ = self.page()
        # Override the base layout to add scroll area properly
        box = page.layout()
        
        title_h = QHBoxLayout()
        import qtawesome as qta
        icon_lbl = label("")
        icon_lbl.setPixmap(qta.icon("fa5s.microchip", color="#f59e0b").pixmap(24, 24))
        title_h.addWidget(icon_lbl)
        t = label("Điều khiển phần cứng", bold=True)
        t.setStyleSheet("font-size: 20px;")
        title_h.addWidget(t)
        title_h.addStretch()
        box.addLayout(title_h)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        c_box = QVBoxLayout(content)
        c_box.setContentsMargins(0, 0, 0, 0)
        c_box.setSpacing(16)
        
        # TCP Gateway Info
        tcp = QFrame()
        tcp.setStyleSheet("background: #cffafe; border: 1px solid #a5f3fc; border-radius: 6px;")
        tcp_l = QHBoxLayout(tcp); tcp_l.setContentsMargins(12, 10, 12, 10)
        info = label("<b>TCP Gateway:</b> Thiết bị thật kết nối vào <code style='background:white;padding:2px 4px;border-radius:4px;color:#0f172a'>host:9001</code> | Protocol: <code style='color:#be123c'>REGISTER {lane_id} DEVICE_TYPE</code> → <code style='color:#be123c'>EVENT {lane_id} {EVENT_TYPE} {json}</code> <a href='#' style='color:#0369a1;text-decoration:none'>Hướng dẫn</a>")
        info.setTextFormat(Qt.TextFormat.RichText); info.setStyleSheet("color: #0369a1; font-size: 13px;")
        info.setOpenExternalLinks(True)
        ico = label("")
        ico.setPixmap(qta.icon("fa5s.network-wired", color="#0369a1").pixmap(16, 16))
        tcp_l.addWidget(ico); tcp_l.addWidget(info); tcp_l.addStretch()
        c_box.addWidget(tcp)
        
        # Split Layout
        split = QHBoxLayout(); split.setSpacing(16)
        
        # Left Panel (Trạng thái thiết bị)
        left = QVBoxLayout(); left.setContentsMargins(0,0,0,0)
        status_card = QFrame(); status_card.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        status_l = QVBoxLayout(status_card); status_l.setContentsMargins(16, 12, 16, 12)
        sh = QHBoxLayout()
        sh_ico = label("")
        sh_ico.setPixmap(qta.icon("fa5s.server", color="#f59e0b").pixmap(16, 16))
        sh.addWidget(sh_ico)
        sh.addWidget(label("Trạng thái thiết bị", bold=True))
        sh.addStretch()
        refresh = icon_btn("fa5s.redo", "", _BTN_PLAIN_STYLE)
        refresh.setFixedSize(28, 28)
        sh.addWidget(refresh)
        status_l.addLayout(sh)
        
        self.dev_grid = QGridLayout(); self.dev_grid.setSpacing(12)
        status_l.addLayout(self.dev_grid)
        status_l.addStretch()
        left.addWidget(status_card); left.addStretch()
        
        # Right Panel
        right = QVBoxLayout(); right.setContentsMargins(0,0,0,0)
        
        # Điều khiển Barrier
        bar_card = QFrame(); bar_card.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        bar_l = QVBoxLayout(bar_card); bar_l.setContentsMargins(16, 12, 16, 12)
        bh = QHBoxLayout()
        bh_ico = label(""); bh_ico.setPixmap(qta.icon("fa5s.road", color="#f59e0b").pixmap(16, 16))
        bh.addWidget(bh_ico); bh.addWidget(label("Điều khiển Barrier", bold=True)); bh.addStretch()
        bar_l.addLayout(bh)
        
        self.bar_list = QVBoxLayout()
        bar_l.addLayout(self.bar_list)
        right.addWidget(bar_card)
        
        # Camera / ANPR
        cam_card = QFrame(); cam_card.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 8px;")
        cam_l = QVBoxLayout(cam_card); cam_l.setContentsMargins(16, 12, 16, 12)
        ch = QHBoxLayout()
        ch_ico = label(""); ch_ico.setPixmap(qta.icon("fa5s.camera", color="#f59e0b").pixmap(16, 16))
        ch.addWidget(ch_ico); ch.addWidget(label("Camera / ANPR", bold=True)); ch.addStretch()
        cam_l.addLayout(ch)
        
        self.cam_lane = QComboBox(); self.cam_lane.setFixedHeight(30)
        cam_l.addWidget(self.cam_lane)
        trig = icon_btn("fa5s.camera", "Kích hoạt chụp ảnh", _BTN_EDIT_STYLE)
        trig.setStyleSheet("background: white; border: 1px solid #3b82f6; color: #3b82f6; border-radius: 6px; padding: 6px;")
        cam_l.addWidget(trig)
        
        upload_lbl = label("Upload ảnh để nhận dạng biển số", "muted")
        upload_lbl.setStyleSheet("font-size: 11px;")
        cam_l.addWidget(upload_lbl)
        upload_btn = QPushButton("Choose File  No file chosen")
        upload_btn.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; color: #64748b; text-align: left;")
        cam_l.addWidget(upload_btn)
        right.addWidget(cam_card)
        
        split.addLayout(left, 2); split.addLayout(right, 1)
        c_box.addLayout(split)
        
        # Simulation
        sim_card = QFrame(); sim_card.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        sim_l = QVBoxLayout(sim_card); sim_l.setContentsMargins(16, 12, 16, 12)
        sim_h = QHBoxLayout()
        sim_ico = label(""); sim_ico.setPixmap(qta.icon("fa5s.flask", color="#f59e0b").pixmap(16, 16))
        sim_h.addWidget(sim_ico)
        sim_h.addWidget(label("Mô phỏng thiết bị (Simulation)", bold=True))
        sim_bdg = label("Không cần phần cứng thật", "badge")
        sim_bdg.setStyleSheet("background: #0ea5e9; color: white; border-radius: 10px; padding: 4px 10px; font-size: 11px;")
        sim_h.addStretch(); sim_h.addWidget(sim_bdg)
        sim_l.addLayout(sim_h)
        
        sim_grid = QGridLayout(); sim_grid.setSpacing(12)
        sim_grid.addWidget(label("Chọn làn", "muted"), 0, 0)
        self.sim_lane = QComboBox(); self.sim_lane.setFixedHeight(30)
        sim_grid.addWidget(self.sim_lane, 1, 0)
        
        sim_grid.addWidget(label("Mã thẻ RFID", "muted"), 0, 1)
        self.sim_rfid = QLineEdit(); self.sim_rfid.setFixedHeight(30); self.sim_rfid.setPlaceholderText("VIS0001")
        sim_grid.addWidget(self.sim_rfid, 1, 1)
        
        sim_grid.addWidget(label("Biển số", "muted"), 0, 2)
        self.sim_plate = QLineEdit(); self.sim_plate.setFixedHeight(30); self.sim_plate.setPlaceholderText("51A-12345")
        sim_grid.addWidget(self.sim_plate, 1, 2)
        
        sim_grid.addWidget(label("Chiều", "muted"), 0, 3)
        self.sim_dir = QComboBox(); self.sim_dir.setFixedHeight(30); self.sim_dir.addItems(["Tự động", "Vào", "Ra"])
        sim_grid.addWidget(self.sim_dir, 1, 3)
        
        sim_btn = icon_btn("fa5s.play", "Mô phỏng quẹt thẻ", _BTN_EDIT_STYLE)
        sim_btn.setStyleSheet("background: #f59e0b; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold;")
        sim_btn.setFixedHeight(30)
        sim_grid.addWidget(sim_btn, 1, 4)
        sim_l.addLayout(sim_grid)
        
        sim_btns = QHBoxLayout()
        car_in = icon_btn("fa5s.car", "Xe đến (loop detector)", _BTN_PLAIN_STYLE)
        car_in.setStyleSheet("background: white; border: 1px solid #3b82f6; color: #3b82f6; border-radius: 6px; padding: 6px 12px;")
        car_out = icon_btn("fa5s.car-side", "Xe đã qua", _BTN_PLAIN_STYLE)
        car_out.setStyleSheet("background: white; border: 1px solid #22c55e; color: #22c55e; border-radius: 6px; padding: 6px 12px;")
        sim_btns.addWidget(car_in); sim_btns.addWidget(car_out); sim_btns.addStretch()
        sim_l.addLayout(sim_btns)
        c_box.addWidget(sim_card)
        
        # Event Log
        log_card = QFrame(); log_card.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px;")
        log_l = QVBoxLayout(log_card); log_l.setContentsMargins(16, 12, 16, 12)
        log_h = QHBoxLayout()
        log_ico = label(""); log_ico.setPixmap(qta.icon("fa5s.terminal", color="#22c55e").pixmap(16, 16))
        log_h.addWidget(log_ico); log_h.addWidget(label("Device event log", bold=True))
        log_btn = QPushButton("Tải log")
        log_btn.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 12px;")
        log_h.addStretch(); log_h.addWidget(log_btn)
        log_l.addLayout(log_h)
        
        self.log_table = self.make_table(["#", "Loại", "Làn", "Dữ liệu", "Thời gian"])
        self.log_table.setFixedHeight(200)
        log_l.addWidget(self.log_table)
        c_box.addWidget(log_card)
        
        scroll.setWidget(content)
        box.addWidget(scroll, 1)
        
        self.load_hardware_ui()
        refresh.clicked.connect(self.load_hardware_ui)
        return page
        
    def load_hardware_ui(self):
        try: lanes = asyncio.run(_lanes(self.settings))
        except: return
        
        self.cam_lane.clear(); self.sim_lane.clear()
        for l in lanes:
            self.cam_lane.addItem(l.name, l.id)
            self.sim_lane.addItem(l.name, l.id)
            
        while self.dev_grid.count():
            item = self.dev_grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        import qtawesome as qta
        for i, l in enumerate(lanes):
            self.dev_grid.addWidget(label(l.name, bold=True), i, 0)
            
            open_bdg = label("Đóng", "badge")
            open_bdg.setStyleSheet("background: #64748b; color: white; border-radius: 10px; padding: 2px 10px; font-size: 11px;")
            self.dev_grid.addWidget(open_bdg, i, 1)
            
            st_bdg = label("Chờ xe", "badge")
            st_bdg.setStyleSheet("background: #0ea5e9; color: white; border-radius: 10px; padding: 2px 10px; font-size: 11px;")
            self.dev_grid.addWidget(st_bdg, i, 2)
            
            d_lay = QHBoxLayout(); d_lay.setSpacing(6); d_lay.setContentsMargins(0,0,0,0)
            for icon_str, text in [("fa5s.id-card", "Đầu đọc thẻ"), ("fa5s.camera", "Camera"), ("fa5s.road", "Barrier"), ("fa5s.fingerprint", "Vân tay")]:
                bdg = QFrame()
                bdg.setStyleSheet("background: #22c55e; border-radius: 4px;")
                bdg_l = QHBoxLayout(bdg); bdg_l.setContentsMargins(6, 2, 6, 2); bdg_l.setSpacing(4)
                ico = label(""); ico.setPixmap(qta.icon(icon_str, color="white").pixmap(10, 10))
                txt = label(text); txt.setStyleSheet("color: white; font-size: 10px; border: none;")
                bdg_l.addWidget(ico); bdg_l.addWidget(txt)
                d_lay.addWidget(bdg)
            d_lay.addStretch()
            w = QWidget(); w.setLayout(d_lay)
            self.dev_grid.addWidget(w, i, 3)
            
        while self.bar_list.count():
            item = self.bar_list.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        for l in lanes:
            bf = QFrame(); bf.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;")
            bl = QHBoxLayout(bf); bl.setContentsMargins(12, 6, 12, 6)
            ico = label(""); ico.setPixmap(qta.icon("fa5s.server", color="#64748b").pixmap(16, 16))
            bl.addWidget(ico)
            bl.addWidget(label(l.name, bold=True))
            bl.addStretch()
            mo = icon_btn("fa5s.door-open", "Mở", _BTN_PLAIN_STYLE)
            mo.setStyleSheet("background: #22c55e; color: white; border: none; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 12px;")
            dong = icon_btn("fa5s.door-closed", "Đóng", _BTN_PLAIN_STYLE)
            dong.setStyleSheet("background: #ef4444; color: white; border: none; border-radius: 4px; padding: 4px 10px; font-weight: bold; font-size: 12px;")
            bl.addWidget(mo); bl.addWidget(dong)
            self.bar_list.addWidget(bf)
            
        self.log_table.setRowCount(1)
        item = QTableWidgetItem("Nhấn \"Tải log\" để xem")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.log_table.setItem(0, 3, item)
