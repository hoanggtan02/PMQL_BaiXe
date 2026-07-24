from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class LanePageMixin:
    def lane_page(self) -> QWidget:
            page, box = self.page(); box.setContentsMargins(16, 16, 16, 16)
            
            # Header
            header = QHBoxLayout()
            history_btn = QPushButton("↺ Lịch sử thay đổi"); history_btn.setStyleSheet("background: white; border: 1px solid #cbd5e1; color: #64748b; border-radius: 6px; padding: 6px 12px;")
            header.addWidget(history_btn)
            
            # Count label updated later
            self.lane_count_lbl = label("| 0 làn đang cấu hình", "muted")
            header.addWidget(self.lane_count_lbl)
            header.addStretch()
            
            add = QPushButton("+ Thêm làn xe"); add.setObjectName("primary")
            add.setStyleSheet("background: #f97316; color: white; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
            add.clicked.connect(self.add_lane)
            header.addWidget(add)
            box.addLayout(header)
            
            # Scroll Area for Grid
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet("background: transparent;")
            self.lane_container = QWidget()
            self.lane_grid = QGridLayout(self.lane_container)
            self.lane_grid.setSpacing(16)
            self.lane_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
            scroll.setWidget(self.lane_container)
            box.addWidget(scroll, 1)
            
            self.load_lanes()
            return page

    def load_lanes(self) -> None:
            if not hasattr(self, "lane_grid"): return
            
            # Clear grid
            while self.lane_grid.count():
                item = self.lane_grid.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            try: lanes = asyncio.run(_lanes(self.settings))
            except Exception: return
            
            self.lane_count_lbl.setText(f"| {len(lanes)} làn đang cấu hình")
            
            for index, lane in enumerate(lanes):
                card = QFrame(); card.setObjectName("card")
                card.setStyleSheet("QFrame#card { background: white; border: none; border-radius: 8px; }")
                cbox = QVBoxLayout(card); cbox.setContentsMargins(20, 20, 20, 20)
                
                # Header: Name + Car count
                header = QHBoxLayout()
                header.addWidget(label(lane.name, bold=True, style="font-size: 16px;"))
                header.addStretch()
                
                count_lbl = label("0", bold=True, style="color: #f59e0b; font-size: 18px;")
                txt_lbl = label("Xe đang gửi", "muted", style="font-size: 10px;")
                vbox = QVBoxLayout(); vbox.setSpacing(0); vbox.addWidget(count_lbl, 0, Qt.AlignmentFlag.AlignHCenter); vbox.addWidget(txt_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
                header.addLayout(vbox)
                cbox.addLayout(header)
                
                # Tags: Direction + Status
                tag_row = QHBoxLayout()
                if lane.direction == "IN": 
                    dir_lbl = label("↗ Xe vào", style="background: #dcfce7; color: #16a34a; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                elif lane.direction == "OUT":
                    dir_lbl = label("↙ Xe ra", style="background: #fee2e2; color: #dc2626; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                else:
                    dir_lbl = label("↔ Hai chiều", style="background: #e0e7ff; color: #4f46e5; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                
                status_lbl = label("● Hoạt động" if lane.is_active else "○ Tắt", style="background: #dcfce7; color: #16a34a; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                if not lane.is_active: status_lbl.setStyleSheet("background: #f1f5f9; color: #64748b; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
                
                tag_row.addWidget(dir_lbl); tag_row.addWidget(status_lbl); tag_row.addStretch()
                cbox.addLayout(tag_row)
                
                cbox.addSpacing(15)
                cbox.addWidget(label("THIẾT BỊ LẮP ĐẶT", "muted", style="font-size: 11px; font-weight: bold;"))
                
                # Devices
                dev_row = QHBoxLayout()
                dev_style = "background: #f0fdf4; color: #16a34a; border: none; border-radius: 6px; padding: 4px 8px; font-size: 11px;"
                if lane.rfid_device_id: dev_row.addWidget(label("💳 Đầu đọc thẻ", style=dev_style))
                if lane.camera_source: dev_row.addWidget(label("📷 Camera", style=dev_style))
                if lane.barrier_device_id: dev_row.addWidget(label("🚧 Barrier", style=dev_style))
                # Assuming finger print is not in our data model but we can show it grayed out if missing, or just not show
                dev_row.addStretch()
                cbox.addLayout(dev_row)
                
                cbox.addSpacing(15)
                cbox.addWidget(label("Trạng thái hoạt động: <b>Chờ xe</b>", style="color: #64748b; font-size: 12px;"))
                cbox.addSpacing(10)
                
                # Actions
                actions = QHBoxLayout()
                edit = icon_btn("fa5s.edit", "Sửa cấu hình", _BTN_EDIT_STYLE)
                edit.setStyleSheet("background: white; border: 1px solid #93c5fd; color: #2563eb; border-radius: 6px; padding: 8px; font-weight: bold;")
                edit.clicked.connect(lambda _=False, item=lane: self.edit_lane(item))
                
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                remove.setStyleSheet("background: white; border: 1px solid #fca5a5; color: #dc2626; border-radius: 6px; padding: 8px 14px;")
                remove.clicked.connect(lambda _=False, item=lane: self.delete_lane(item))
                
                actions.addWidget(edit, 1)
                actions.addWidget(remove)
                cbox.addLayout(actions)
                
                self.lane_grid.addWidget(card, index // 2, index % 2)

    def show_lane_modal(self, lane=None):
            title = "Thêm làn xe" if not lane else "Sửa làn xe"
            dialog, content, footer = modal_shell(self, title, 520)
            form = QFormLayout(); content.addLayout(form)
            name = QLineEdit(lane.name if lane else "")
            name.setPlaceholderText("Ví dụ: Làn vào 1, Làn ra A")
            direction = QComboBox(); direction.addItem("Xe vào", "IN"); direction.addItem("Xe ra", "OUT"); direction.addItem("Hai chiều", "BIDIRECTIONAL")
            status = QComboBox(); status.addItem("Hoạt động", True); status.addItem("Tắt", False)
            if lane:
                direction.setCurrentIndex(max(0, direction.findData(lane.direction)))
                status.setCurrentIndex(0 if lane.is_active else 1)
            form.addRow("Tên làn *", name); form.addRow("Chiều xe", direction); form.addRow("Trạng thái", status)
            hint = label("Thiết bị có thể được gán ở mục Kết nối thiết bị sau khi lưu làn.", "muted")
            hint.setWordWrap(True); content.addWidget(hint)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu cấu hình")
            save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            camera = lane.camera_source if lane else "cam1"
            rfid = lane.rfid_device_id if lane else "rfid1"
            barrier = lane.barrier_device_id if lane else "bar1"
            
            def do_save():
                try:
                    is_active = bool(status.currentData())
                    selected_dir = direction.currentData()
                    if lane:
                        asyncio.run(_update_lane(self.settings, lane.id, name.text(), selected_dir, camera, rfid, barrier, is_active))
                    else:
                        asyncio.run(_create_lane(self.settings, name.text(), selected_dir, camera, rfid, barrier))
                    self.load_lanes()
                    if hasattr(self, 'reload_page'): self.reload_page('operations')
                    dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save.clicked.connect(do_save); dialog.exec()

    def add_lane(self) -> None:
            
            self.show_lane_modal()

    def edit_lane(self, lane) -> None:
            self.show_lane_modal(lane)

    def delete_lane(self, lane) -> None:
            if QMessageBox.question(self, "Xóa làn", f"Xóa mềm làn '{lane.name}'?") != QMessageBox.StandardButton.Yes: return
            try: 
                asyncio.run(_delete_lane(self.settings, lane.id))
                self.load_lanes()
                if hasattr(self, 'reload_page'): self.reload_page('operations')
            except Exception as exc: show_toast(self, str(exc), "error")

