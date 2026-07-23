from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class Vehicle_typePageMixin:
    def vehicle_type_page(self) -> QWidget:
            page, box = self.page()
            row = QHBoxLayout(); title = label("Cấu hình loại xe", bold=True); title.setStyleSheet("font-size:24px;"); row.addWidget(title); row.addStretch()
            add = QPushButton("+ Thêm loại xe"); add.setObjectName("primary"); add.clicked.connect(self.add_vehicle_type); row.addWidget(add); box.addLayout(row)
            box.addWidget(label("Các biểu mẫu thuê bao, biểu phí và xe vào đều dùng danh mục này.", "muted"))
            self.vehicle_type_table = self.make_table(["Mã dùng trong hệ thống", "Tên hiển thị", "Thao tác"], 6); box.addWidget(self.vehicle_type_table, 1); self.load_vehicle_types()
            return page

    def load_vehicle_types(self) -> None:
            if not hasattr(self, "vehicle_type_table"): return
            try: rows = asyncio.run(_vehicle_types(self.settings))
            except Exception as exc: show_toast(self, str(exc), "error"); return
            self.vehicle_type_table.setRowCount(len(rows))
            for r, item in enumerate(rows):
                self.vehicle_type_table.setItem(r, 0, QTableWidgetItem(item.code))
                self.vehicle_type_table.setItem(r, 1, QTableWidgetItem(item.display_name))
                actions = QWidget(); actions.setMinimumHeight(38); action_row = QHBoxLayout(actions); action_row.setContentsMargins(4, 2, 4, 2)
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE); remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                edit.clicked.connect(lambda _=False, row=item: self.edit_vehicle_type(row)); remove.clicked.connect(lambda _=False, row=item: self.delete_vehicle_type(row))
                action_row.addWidget(edit); action_row.addWidget(remove); self.vehicle_type_table.setCellWidget(r, 2, actions)

    def vehicle_type_dialog(self, item=None) -> None:
            dialog, content, footer = modal_shell(self, "Sửa loại xe" if item else "Thêm loại xe", 520)
            form = QFormLayout(); content.addLayout(form)
            code = QLineEdit(item.code if item else ""); name = QLineEdit(item.display_name if item else "")
            code.setPlaceholderText("Ví dụ: electric_bike"); name.setPlaceholderText("Ví dụ: Xe đạp điện")
            form.addRow("Mã loại xe *", code); form.addRow("Tên hiển thị *", name)
            hint = label("Mã chỉ dùng để liên kết dữ liệu; người dùng sẽ luôn thấy tên hiển thị.", "muted"); hint.setWordWrap(True); content.addWidget(hint)
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu loại xe"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            def save_item() -> None:
                try:
                    if item: asyncio.run(_update_vehicle_type(self.settings, item.id, code.text(), name.text()))
                    else: asyncio.run(_create_vehicle_type(self.settings, code.text(), name.text()))
                    dialog.accept(); self.reload_page("vehicle_types")
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save.clicked.connect(save_item); dialog.exec()

    def add_vehicle_type(self) -> None:
            self.vehicle_type_dialog()

    def edit_vehicle_type(self, item) -> None:
            self.vehicle_type_dialog(item)

    def delete_vehicle_type(self, item) -> None:
            if QMessageBox.question(self, "Xóa loại xe", f"Xóa mềm loại xe '{item.display_name}'?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_vehicle_type(self.settings, item.id)); self.reload_page("vehicle_types")
            except Exception as exc: show_toast(self, str(exc), "error")

