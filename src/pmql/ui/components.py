"""Reusable visual components for the PMQL PySide6 desktop application."""
from __future__ import annotations


LIGHT_THEME = """
* { font-family: 'Segoe UI', 'Inter', Arial, sans-serif; font-size: 13px; color: #1e293b; outline: none; }
QMainWindow, QWidget#root, QWidget#page { background: #f8fafc; }
QFrame#sidebar { background: #0f172a; border-right: 1px solid #1e293b; }
QFrame#sidebar QLabel { color: #f1f5f9; }
QFrame#header { background: #ffffff; border-bottom: 1px solid #e2e8f0; }
QFrame#card, QFrame#panel { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
QDialog { background: #ffffff; border-radius: 12px; }
QLabel#muted { color: #64748b; }
QLabel#section { color: #94a3b8; font-size: 11px; font-weight: 700; padding: 16px 14px 8px; text-transform: uppercase; letter-spacing: 0.5px; }
QLabel#badge { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; border-radius: 12px; padding: 4px 10px; font-size: 11px; font-weight: 700; }
QLabel#metricValue { font-size: 28px; font-weight: 800; color: #0f172a; }
QLabel#metricCaption { color: #64748b; font-size: 12px; font-weight: 600; }
QLineEdit, QComboBox { color: #0f172a; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 14px; font-size: 13px; }
QLineEdit:focus, QComboBox:focus { border: 2px solid #f97316; }
QPushButton { background: #ffffff; color: #334155; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 16px; font-weight: 600; font-size: 13px; }
QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; }
QPushButton#nav { color: #94a3b8; background: transparent; border: 0; text-align: left; padding: 12px 16px; border-radius: 8px; margin: 2px 10px; }
QPushButton#nav:hover { background: #1e293b; color: #f8fafc; }
QPushButton#nav[active='true'] { background: #ffedd5; color: #ea580c; border: 1px solid #fdba74; font-weight: 700; }
QPushButton#primary { background: #f97316; color: white; border: 1px solid #ea580c; }
QPushButton#primary:hover { background: #ea580c; }
QPushButton#success { background: #10b981; color: white; border: 1px solid #059669; }
QPushButton#success:hover { background: #059669; }
QPushButton#danger { background: #ef4444; color: white; border: 1px solid #dc2626; }
QPushButton#danger:hover { background: #dc2626; }
QPushButton#warning { background: #f59e0b; color: white; border: 1px solid #d97706; }
QPushButton#warning:hover { background: #d97706; }
QTableWidget { background: #ffffff; alternate-background-color: #f8fafc; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 12px; gridline-color: #f1f5f9; selection-background-color: #ffedd5; selection-color: #0f172a; outline: none; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid #f1f5f9; }
QListWidget { background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; }
QListWidget::item { color: #0f172a; padding: 8px; border-radius: 6px; margin-bottom: 2px; } 
QListWidget::item:selected { background: #ffedd5; color: #ea580c; font-weight: 600; }
QHeaderView::section { background: #f8fafc; color: #64748b; border: 0; border-bottom: 1px solid #e2e8f0; padding: 12px; font-weight: 700; text-align: left; }
QScrollBar:vertical { background: #f8fafc; width: 8px; margin: 0px; border-radius: 4px; } 
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QFrame#modalHeader { background: #ffffff; border-bottom: 1px solid #e2e8f0; border-top-left-radius: 12px; border-top-right-radius: 12px; }
QFrame#modalFooter { background: #f8fafc; border-top: 1px solid #e2e8f0; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
QMessageBox { background: #ffffff; border-radius: 12px; }
QMessageBox QLabel { color: #0f172a; min-width: 300px; font-size: 14px; }
QComboBox QAbstractItemView { background: #ffffff; color: #0f172a; selection-background-color: #ffedd5; selection-color: #ea580c; border: 1px solid #cbd5e1; border-radius: 8px; padding: 4px; }
QComboBox::drop-down { border: 0; padding-right: 10px; }
QToolTip { color: #ffffff; background: #0f172a; border: 0; padding: 8px 12px; border-radius: 6px; font-size: 12px; }
QProgressBar { background-color: #f1f5f9; border: 0; border-radius: 4px; text-align: center; color: transparent; }
QProgressBar::chunk { background-color: #10b981; border-radius: 4px; }
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
