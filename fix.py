import re

with open('src/pmql/ui/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix Cards action buttons
old_cards = """                status_cb = QComboBox()
                status_cb.addItem("Đổi trạng thái", "")
                status_cb.addItem("Có sẵn", "AVAILABLE"); status_cb.addItem("Đang dùng", "IN_USE")
                status_cb.addItem("Đã mất", "LOST"); status_cb.addItem("Bị khóa", "LOCKED")
                status_cb.setStyleSheet("QComboBox { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 8px; font-size: 12px; } QComboBox::drop-down { border: none; width: 20px; }")
                
                def _change_card_status(idx, item_card=card, cb=status_cb):
                    val = cb.itemData(idx)
                    if not val: return
                    try:
                        asyncio.run(_update_card(settings, item_card.id, item_card.card_type, item_card.subscriber_id, val))
                        self.reload_page("cards")
                    except Exception as e:
                        QMessageBox.warning(self, "Lỗi", str(e))
                status_cb.currentIndexChanged.connect(_change_card_status)
                
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                edit.clicked.connect(lambda _=False, item=card: self.edit_card(item))
                remove.clicked.connect(lambda _=False, item=card: self.delete_card(item))
                actions_row.addWidget(status_cb); actions_row.addWidget(edit); actions_row.addWidget(remove)"""

new_cards = """                status_btn = icon_btn("fa5s.sync", "Đổi TT", _BTN_PLAIN_STYLE)
                
                def _show_status_menu(item_card=card, btn=status_btn):
                    from PySide6.QtWidgets import QMenu
                    from PySide6.QtCore import QPoint
                    menu = QMenu(self.card_table)
                    menu.setStyleSheet("QMenu { background: white; border: 1px solid #cbd5e1; border-radius: 6px; } QMenu::item { padding: 6px 24px; } QMenu::item:selected { background: #f1f5f9; }")
                    for text, val in [("Có sẵn", "AVAILABLE"), ("Đang dùng", "IN_USE"), ("Đã mất", "LOST"), ("Bị khóa", "LOCKED")]:
                        action = menu.addAction(text)
                        action.triggered.connect(lambda _, v=val, c=item_card: _change_card_status(v, c))
                    menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))
                    
                def _change_card_status(val, item_card):
                    try:
                        asyncio.run(_update_card(settings, item_card.id, item_card.card_type, item_card.subscriber_id, val))
                        self.reload_page("cards")
                    except Exception as e:
                        QMessageBox.warning(self, "Lỗi", str(e))
                status_btn.clicked.connect(lambda _=False: _show_status_menu())
                
                edit = icon_btn("fa5s.edit", "Sửa", _BTN_EDIT_STYLE)
                remove = icon_btn("fa5s.trash-alt", "Xóa", _BTN_DEL_STYLE)
                edit.clicked.connect(lambda _=False, item=card: self.edit_card(item))
                remove.clicked.connect(lambda _=False, item=card: self.delete_card(item))
                actions_row.addWidget(status_btn); actions_row.addWidget(edit); actions_row.addWidget(remove)"""

if old_cards in content:
    content = content.replace(old_cards, new_cards)
    print('Replaced cards action buttons successfully.')
else:
    print('ERROR: Could not find old_cards exactly.')

# 2. Fix make_table action_col_width
content = content.replace('def make_table(self, headers: list[str], minimum_rows: int = 10, action_col_width: int = 250) -> QTableWidget:', 
                          'def make_table(self, headers: list[str], minimum_rows: int = 10, action_col_width: int = 300) -> QTableWidget:')

# Write back
with open('src/pmql/ui/app.py', 'w', encoding='utf-8') as f:
    f.write(content)
