"""Reusable visual components for the PMQL PySide6 desktop application."""
from __future__ import annotations


LIGHT_THEME = """
* { font-family: 'Segoe UI', 'Inter', Arial, sans-serif; font-size: 13px; color: #1e293b; outline: none; }
QMainWindow, QWidget#root, QWidget#page { background: #f8fafc; }
QWidget#page { min-width: 0; }

/* ── Sidebar ─────────────────────────────────────────────── */
QFrame#sidebar { background: #0f172a; border: none; }
QFrame#sidebar QLabel { color: #cbd5e1; border: none; }
QFrame#sidebar QLabel#sidebarBrand { color: #ffffff; font-size: 14px; font-weight: 700; }
QFrame#sidebar QLabel#sidebarSub { color: #64748b; font-size: 11px; }
QFrame#sidebar QLabel#section { color: #475569; font-size: 10px; font-weight: 700; padding: 16px 20px 6px; letter-spacing: 1.5px; text-transform: uppercase; }
QPushButton#nav { color: #94a3b8; background: transparent; border: none; border-left: 3px solid transparent; text-align: left; padding: 10px 16px 10px 17px; border-radius: 0px; margin: 1px 0px; font-size: 13px; }
QPushButton#nav:hover { background: rgba(255,255,255,0.06); color: #e2e8f0; border-left: 3px solid #334155; }
QPushButton#nav[active='true'] { background: rgba(249,115,22,0.12); color: #f97316; border-left: 3px solid #f97316; font-weight: 700; }

/* ── Header ──────────────────────────────────────────────── */
QFrame#header { background: #ffffff; border: none; border-bottom: 1px solid #e2e8f0; }

/* ── Cards & Panels ──────────────────────────────────────── */
QFrame#card, QFrame#panel { background: #ffffff; border: none; border-radius: 12px; }
QFrame#surface { background: #ffffff; border: none; border-radius: 8px; }
QFrame#softSurface { background: #f8fafc; border: none; border-radius: 8px; }

/* ── Dialogs ─────────────────────────────────────────────── */
QDialog { background: #ffffff; border-radius: 12px; }
QFrame#modalHeader { background: #ffffff; border-bottom: 1px solid #e2e8f0; border-top-left-radius: 12px; border-top-right-radius: 12px; }
QFrame#modalFooter { background: #f8fafc; border-top: 1px solid #e2e8f0; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
QMessageBox { background: #ffffff; border-radius: 12px; }
QMessageBox QLabel { color: #0f172a; min-width: 300px; font-size: 14px; }

/* ── Labels ──────────────────────────────────────────────── */
QLabel#muted { color: #64748b; }
QLabel#badge { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700; }
QLabel#badge_warn { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700; }
QLabel#badge_danger { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700; }
QLabel#badge_info { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700; }
QLabel#badge_neutral { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700; }
QLabel#metricValue { font-size: 32px; font-weight: 800; color: #0f172a; }
QLabel#metricCaption { color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
QLabel#pageTitle { font-size: 24px; font-weight: 700; color: #0f172a; }
QLabel#pageSubtitle { font-size: 13px; color: #64748b; }
QLabel#sectionTitle { font-size: 13px; font-weight: 700; color: #0f172a; }

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit, QComboBox, QDateEdit, QDateTimeEdit { color: #0f172a; background: #f8fafc; border: none; border-bottom: 1px solid #cbd5e1; border-radius: 4px; padding: 10px 14px; font-size: 13px; min-height: 18px; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus { background: #ffffff; border-bottom: 2px solid #f97316; }
QLineEdit:read-only { color: #64748b; background: #f1f5f9; }
QComboBox QAbstractItemView { background: #ffffff; color: #0f172a; selection-background-color: #fff7ed; selection-color: #ea580c; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; }
QComboBox::drop-down { border: 0; padding-right: 10px; }
QDateEdit::drop-down, QDateTimeEdit::drop-down { border: 0; padding-right: 8px; }
QFormLayout QLabel { color: #475569; font-size: 12px; font-weight: 600; }

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton { background: #ffffff; color: #334155; border: 1px solid #e2e8f0; border-radius: 8px; padding: 9px 16px; font-weight: 600; font-size: 13px; }
QPushButton:hover { background: #f8fafc; border-color: #cbd5e1; }
QPushButton:pressed { background: #f1f5f9; }
QPushButton#primary { background: #f97316; color: white; border: none; }
QPushButton#primary:hover { background: #ea580c; }
QPushButton#success { background: #10b981; color: white; border: none; }
QPushButton#success:hover { background: #059669; }
QPushButton#danger { background: #ef4444; color: white; border: none; }
QPushButton#danger:hover { background: #dc2626; }
QPushButton#warning { background: #f59e0b; color: white; border: none; }
QPushButton#warning:hover { background: #d97706; }
QPushButton#ghost { background: transparent; color: #64748b; border: 1px solid #e2e8f0; }
QPushButton#ghost:hover { background: #f8fafc; color: #0f172a; }
QPushButton:disabled { background: #e2e8f0; color: #94a3b8; border: none; }

/* ── Tables ──────────────────────────────────────────────── */
QTableWidget { background: #ffffff; alternate-background-color: #f8fafc; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; gridline-color: #f1f5f9; selection-background-color: #fff7ed; selection-color: #0f172a; outline: none; }
QTableWidget::item { padding: 10px 8px; border-bottom: 1px solid #f1f5f9; }
QTableWidget::item:hover { background: #fff7ed; }
QHeaderView::section { background: #f8fafc; color: #64748b; border: 0; border-bottom: 2px solid #e2e8f0; padding: 10px 8px; font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; text-align: left; }

/* ── Lists ───────────────────────────────────────────────── */
QListWidget { background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; }
QListWidget::item { color: #0f172a; padding: 8px; border-radius: 6px; margin-bottom: 2px; }
QListWidget::item:hover { background: #fff7ed; }
QListWidget::item:selected { background: #fff7ed; color: #ea580c; font-weight: 600; }
QGroupBox { background: #ffffff; border: none; border-radius: 8px; margin-top: 12px; padding: 12px; font-weight: 700; color: #0f172a; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
QCheckBox { spacing: 8px; color: #475569; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { background: #f97316; border-color: #f97316; }

/* ── Scrollbars ──────────────────────────────────────────── */
QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 3px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 6px; margin: 0; }
QScrollBar::handle:horizontal { background: #cbd5e1; border-radius: 3px; min-width: 24px; }

/* ── Misc ────────────────────────────────────────────────── */
QToolTip { color: #ffffff; background: #0f172a; border: 0; padding: 8px 12px; border-radius: 6px; font-size: 12px; }
QProgressBar { background-color: #e2e8f0; border: 0; border-radius: 4px; text-align: center; color: transparent; }
QProgressBar::chunk { background-color: #f97316; border-radius: 4px; }
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab { background: transparent; color: #64748b; padding: 8px 20px; border-bottom: 2px solid transparent; font-weight: 600; }
QTabBar::tab:selected { color: #f97316; border-bottom: 2px solid #f97316; }
QTabBar::tab:hover { color: #0f172a; }
QScrollArea { border: none; background: transparent; }
"""


def modal_shell(parent, title: str, minimum_width: int = 620):
    """Return a consistently styled dialog with header/content/footer layouts."""
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(minimum_width)
    dialog.setStyleSheet(LIGHT_THEME)
    root = QVBoxLayout(dialog)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    header = QFrame(); header.setObjectName("modalHeader")
    header_row = QHBoxLayout(header); header_row.setContentsMargins(24, 18, 16, 18)
    heading = QLabel(title); heading.setStyleSheet("font-size:18px; font-weight:700; color:#0f172a;")
    close = QPushButton("×"); close.setFixedSize(32, 32)
    close.setCursor(Qt.CursorShape.PointingHandCursor)
    close.setStyleSheet("QPushButton { font-size:22px; border:none; color:#94a3b8; background: transparent; border-radius: 16px; } QPushButton:hover { background: #f1f5f9; color:#0f172a; }")
    close.clicked.connect(dialog.reject)
    header_row.addWidget(heading); header_row.addStretch(); header_row.addWidget(close)
    content = QWidget(); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(24, 20, 24, 20)
    footer = QFrame(); footer.setObjectName("modalFooter")
    footer_layout = QHBoxLayout(footer); footer_layout.setContentsMargins(24, 14, 24, 14)
    root.addWidget(header); root.addWidget(content); root.addWidget(footer)
    # Footer actions are attached by the caller after this helper returns.
    QTimer.singleShot(0, lambda: [button.setCursor(Qt.CursorShape.PointingHandCursor) for button in dialog.findChildren(QPushButton)])
    return dialog, content_layout, footer_layout
