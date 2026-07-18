"""Reusable visual components for the PMQL PySide6 desktop application."""
from __future__ import annotations


LIGHT_THEME = """
* { font-family: 'Segoe UI', Arial; font-size: 13px; color: #162033; }
QMainWindow, QWidget#root, QWidget#page { background: #f4f7fb; }
QFrame#sidebar { background: #111a2a; border: 0; }
QFrame#sidebar QLabel { color: #f8fafc; }
QFrame#header { background: #ffffff; border: 0; border-bottom: 1px solid #e5eaf2; }
QFrame#card, QFrame#panel { background: #ffffff; border: 1px solid #e0e7f0; border-radius: 12px; }
QDialog { background: #ffffff; }
QLabel#muted { color: #718096; }
QLabel#section { color: #7b8799; font-size: 10px; font-weight: 700; padding: 12px 14px 5px; }
QLabel#badge { background: #e7f8ed; color: #138a48; border: 1px solid #aae9bd; border-radius: 10px; padding: 4px 9px; font-size: 10px; font-weight: 700; }
QLabel#metricValue { font-size: 27px; font-weight: 800; color: #172033; }
QLabel#metricCaption { color: #64748b; font-size: 11px; font-weight: 700; }
QLineEdit, QComboBox { color: #172033; background: #ffffff; border: 1px solid #d8e1ec; border-radius: 8px; padding: 10px 12px; }
QLineEdit:focus, QComboBox:focus { border: 2px solid #ff8a32; }
QPushButton { background: #ffffff; color: #344054; border: 1px solid #d8e1ec; border-radius: 8px; padding: 9px 14px; font-weight: 700; }
QPushButton:hover { background: #f6f8fb; border-color: #b7c4d4; }
QPushButton#nav { color: #bec8d5; background: transparent; border: 0; text-align: left; padding: 11px 14px; }
QPushButton#nav:hover { background: #1d2a40; color: white; }
QPushButton#nav[active='true'] { background: #372b27; color: #ff913c; border: 1px solid #6a402b; }
QPushButton#primary { background: #ff7a1a; color: white; border: 1px solid #ff7a1a; }
QPushButton#primary:hover { background: #e9660b; }
QPushButton#success { background: #13a855; color: white; border: 1px solid #13a855; }
QPushButton#danger { background: #ee3d46; color: white; border: 1px solid #ee3d46; }
QTableWidget { background: #ffffff; alternate-background-color: #f8fafc; color: #172033; border: 1px solid #e0e7f0; border-radius: 9px; gridline-color: #edf1f5; selection-background-color: #fff0e4; selection-color: #172033; }
QListWidget { background: #ffffff; color: #172033; border: 1px solid #d8e1ec; border-radius: 8px; padding: 5px; }
QListWidget::item { color: #172033; padding: 7px; } QListWidget::item:selected { background: #fff0e4; color: #172033; }
QHeaderView::section { background: #f7f9fc; color: #60708a; border: 0; border-bottom: 1px solid #e0e7f0; padding: 11px; font-weight: 800; }
QScrollBar:vertical { background: #f4f7fb; width: 10px; } QScrollBar::handle:vertical { background: #c3cedb; border-radius: 5px; }
QFrame#modalHeader { background: #ffffff; border-bottom: 1px solid #e5eaf2; border-top-left-radius: 12px; border-top-right-radius: 12px; }
QFrame#modalFooter { background: #f8fafc; border-top: 1px solid #e5eaf2; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
QDialog QLabel { color: #172033; }
QMessageBox { background: #ffffff; }
QMessageBox QLabel { color: #172033; min-width: 280px; }
QComboBox QAbstractItemView { background: #ffffff; color: #172033; selection-background-color: #fff0e4; selection-color: #172033; border: 1px solid #d8e1ec; }
QToolTip { color: #ffffff; background: #172033; border: 0; padding: 6px; }
"""


def modal_shell(parent, title: str, minimum_width: int = 620):
    """Return a consistently styled dialog with header/content/footer layouts."""
    from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(minimum_width)
    dialog.setStyleSheet(LIGHT_THEME)
    root = QVBoxLayout(dialog)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    header = QFrame(); header.setObjectName("modalHeader")
    header_row = QHBoxLayout(header); header_row.setContentsMargins(20, 16, 16, 16)
    heading = QLabel(title); heading.setStyleSheet("font-size:20px; font-weight:700; color:#172033;")
    close = QPushButton("×"); close.setFixedSize(32, 32); close.setStyleSheet("font-size:24px; border:0; color:#667085;")
    close.clicked.connect(dialog.reject)
    header_row.addWidget(heading); header_row.addStretch(); header_row.addWidget(close)
    content = QWidget(); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(20, 18, 20, 18)
    footer = QFrame(); footer.setObjectName("modalFooter")
    footer_layout = QHBoxLayout(footer); footer_layout.setContentsMargins(20, 14, 20, 14)
    root.addWidget(header); root.addWidget(content); root.addWidget(footer)
    return dialog, content_layout, footer_layout
