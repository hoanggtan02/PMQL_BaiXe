from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class CardPageMixin:
    def card_page(self) -> QWidget:
            page, box = self.page(); row = QHBoxLayout(); title = label("Quản lý thẻ RFID", bold=True); title.setStyleSheet("font-size:24px;"); row.addWidget(title); row.addStretch(); add = QPushButton("+ Thêm thẻ"); add.setObjectName("primary"); add.clicked.connect(self.add_card); row.addWidget(add); box.addLayout(row)
            self.card_table = self.make_table(["Mã thẻ (UID)", "Loại thẻ", "Thuê bao", "Trạng thái", "Thao tác"], action_col_width=300); box.addWidget(self.card_table, 1); self.load_cards(); return page

    def load_cards(self) -> None:
            if not hasattr(self, "card_table"): return
            try: cards = asyncio.run(_card_display_rows(self.settings))
            except Exception: return
            self.card_table.setRowCount(len(cards))
            
            STATUS_MAP = {"AVAILABLE": "Có sẵn", "IN_USE": "Đang dùng", "LOST": "Đã mất", "LOCKED": "Bị khóa"}
            STATUS_COLOR = {"AVAILABLE": "#22c55e", "IN_USE": "#3b82f6", "LOST": "#f59e0b", "LOCKED": "#ef4444"}
            
            for r, (card, subscriber_name) in enumerate(cards):
                card_type_display = "Thuê bao" if card.card_type == "SUBSCRIBER" else "Vãng lai"
                status_text = STATUS_MAP.get(card.status, card.status)
    
                # Center-align cell items
                for c, value in enumerate((card.rfid_code, card_type_display, subscriber_name if card.card_type == "SUBSCRIBER" else "—")):
                    cell = QTableWidgetItem(str(value))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.card_table.setItem(r, c, cell)
    
                # Status badge widget (centered) — sized to fit its text so it never gets clipped
                status_w = QWidget(); sl = QHBoxLayout(status_w); sl.setContentsMargins(4, 6, 4, 6); sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_lbl = label(status_text, "badge", True)
                status_lbl.setStyleSheet(
                    f"background: {STATUS_COLOR.get(card.status, '#94a3b8')}; color: white; "
                    "padding: 4px 12px; border-radius: 10px; font-weight: bold; font-size: 12px;"
                )
                status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                status_lbl.adjustSize(); status_lbl.setMinimumWidth(status_lbl.sizeHint().width())
                sl.addWidget(status_lbl)
                self.card_table.setItem(r, 3, QTableWidgetItem(""))
                self.card_table.setCellWidget(r, 3, status_w)
    
                # Action buttons — same icon style as the Subscribers page
                actions = QWidget(); actions.setMinimumHeight(38); actions_row = QHBoxLayout(actions); actions_row.setContentsMargins(6, 4, 6, 4); actions_row.setSpacing(6)
                
                status_combo = QComboBox()
                status_combo.setMinimumHeight(32)
                status_combo.setMinimumWidth(130)
                status_combo.addItem("↻ Đổi TT", "")
                for text, val in [("Có sẵn", "AVAILABLE"), ("Đang dùng", "IN_USE"), ("Đã mất", "LOST"), ("Bị khóa", "LOCKED")]:
                    status_combo.addItem(text, val)
                    
                def _change_card_status(index, item_card=card, combo=status_combo):
                    val = combo.itemData(index)
                    if not val: return
                    try:
                        asyncio.run(_update_card(self.settings, item_card.id, item_card.card_type, item_card.subscriber_id, val))
                        show_toast(self, "Đổi trạng thái thành công!", "success")
                        self.reload_page("cards")
                    except Exception as e:
                        show_toast(self, str(e), "error")
                        combo.setCurrentIndex(0)
                        
                status_combo.currentIndexChanged.connect(_change_card_status)
                
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                edit.clicked.connect(lambda _=False, item=card: self.edit_card(item))
                remove.clicked.connect(lambda _=False, item=card: self.delete_card(item))
                actions_row.addWidget(status_combo); actions_row.addWidget(edit); actions_row.addWidget(remove)
                self.card_table.setItem(r, 4, QTableWidgetItem(""))
                self.card_table.setCellWidget(r, 4, actions)
                self.card_table.setRowHeight(r, 56)

    def add_card(self) -> None:
            self.card_dialog()

    def edit_card(self, card) -> None:
            self.card_dialog(card)

    def card_dialog(self, card=None) -> None:
            dialog, content, footer = modal_shell(self, "Thêm thẻ RFID" if not card else "Sửa thẻ RFID", 560)
            form = QFormLayout(); content.addLayout(form)
            
            uid = QLineEdit(card.rfid_code if card else ""); uid.setPlaceholderText("Quét hoặc nhập mã UID")
            if card: uid.setReadOnly(True)
            
            card_type = QComboBox(); card_type.addItem("Vãng lai", "GUEST"); card_type.addItem("Thuê bao", "SUBSCRIBER")
            
            subscriber = QComboBox(); subscriber.addItem("Chưa gán thuê bao", None)
            try:
                for item in asyncio.run(_subscriber_entities(self.settings)): subscriber.addItem(f"{item.full_name} — {item.phone}", item.id)
            except Exception: pass
            
            if card:
                card_type.setCurrentIndex(max(0, card_type.findData(card.card_type)))
                subscriber.setCurrentIndex(max(0, subscriber.findData(card.subscriber_id)))
            
            # Hide subscriber combo if card type is GUEST
            def type_changed():
                subscriber.setVisible(card_type.currentData() == "SUBSCRIBER")
            card_type.currentIndexChanged.connect(type_changed); type_changed()
            
            status = QComboBox()
            status.addItem("Có sẵn", "AVAILABLE"); status.addItem("Đang dùng", "IN_USE")
            status.addItem("Đã mất", "LOST"); status.addItem("Bị khóa", "LOCKED")
            if card: status.setCurrentIndex(max(0, status.findData(card.status)))
            
            form.addRow("Mã thẻ UID *", uid); form.addRow("Loại thẻ", card_type); form.addRow("Gán thuê bao", subscriber)
            if card: form.addRow("Trạng thái", status)
            
            cancel, save = QPushButton("Hủy"), QPushButton("Lưu thẻ" if not card else "Lưu thay đổi"); save.setObjectName("primary"); footer.addStretch(); footer.addWidget(cancel); footer.addWidget(save); cancel.clicked.connect(dialog.reject)
            
            def save_card() -> None:
                try:
                    c_type, s_id = card_type.currentData(), subscriber.currentData()
                    if c_type == "GUEST": s_id = None
                    if card:
                        asyncio.run(_update_card(self.settings, card.id, c_type, s_id, status.currentData()))
                    else:
                        asyncio.run(_create_card(self.settings, uid.text(), c_type, s_id))
                    self.load_cards(); dialog.accept()
                except Exception as exc: show_toast(dialog, str(exc), "error")
            save.clicked.connect(save_card); dialog.exec()

    def delete_card(self, card) -> None:
            if QMessageBox.question(self, "Xóa thẻ", f"Xóa mềm thẻ {card.rfid_code}?") != QMessageBox.StandardButton.Yes: return
            try: asyncio.run(_delete_card(self.settings, card.id)); self.load_cards()
            except Exception as exc: show_toast(self, str(exc), "error")

