from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtCharts import (
    QChart, QChartView, QLineSeries, QPieSeries, QPieSlice,
    QAreaSeries, QValueAxis
)
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import datetime, date, timedelta


class ReportPageMixin:
    def reports_page(self) -> QWidget:
        page, box = self.page()
        box.setContentsMargins(24, 20, 24, 24)
        box.setSpacing(16)

        # ── Top filter bar ─────────────────────────────────────────────
        filter_row = QHBoxLayout(); filter_row.setSpacing(8)

        lbl_range = label("Khoảng thời gian", "muted")
        lbl_range.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        filter_row.addWidget(lbl_range)
        filter_row.addSpacing(8)

        period_btns = []
        for i, text in enumerate(["Hôm nay", "7 ngày", "Tháng này", "Tùy chọn"]):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            active_style = "QPushButton { background: #f97316; color: white; border: none; border-radius: 14px; padding: 6px 16px; font-weight: 700; font-size: 12px; }"
            idle_style   = "QPushButton { background: white; color: #475569; border: 1px solid #e2e8f0; border-radius: 14px; padding: 6px 16px; font-weight: 600; font-size: 12px; } QPushButton:hover { background: #f8fafc; }"
            btn.setStyleSheet(active_style if i == 0 else idle_style)
            period_btns.append((btn, active_style, idle_style))
            filter_row.addWidget(btn)

        def select_period(idx):
            for j, (b, a_s, i_s) in enumerate(period_btns):
                b.setStyleSheet(a_s if j == idx else i_s)

        for i, (btn, _, _) in enumerate(period_btns):
            btn.clicked.connect(lambda _, i=i: select_period(i))

        filter_row.addStretch()

        # Right-side action buttons
        btn_view = QPushButton("🔍  Xem báo cáo")
        btn_view.setObjectName("primary")
        btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view.setStyleSheet("QPushButton { background: #f97316; color: white; border: none; border-radius: 8px; padding: 8px 18px; font-weight: 700; font-size: 13px; } QPushButton:hover { background: #ea580c; }")

        btn_export = QPushButton("📥  Xuất  ▾")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet("QPushButton { background: white; color: #475569; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 16px; font-weight: 600; font-size: 13px; } QPushButton:hover { background: #f8fafc; }")

        filter_row.addWidget(btn_view)
        filter_row.addWidget(btn_export)
        box.addLayout(filter_row)

        # ── 4 Summary metric cards ──────────────────────────────────────
        cards_row = QHBoxLayout(); cards_row.setSpacing(14)
        metric_defs = [
            ("Tổng doanh thu",     "0 đ", "💵 Đã thu",          "#fff7ed", "#ea580c"),
            ("Tổng lượt gửi",     "0",   "🚗 Xe hoàn thành",   "#eff6ff", "#3b82f6"),
            ("Doanh thu vãng lai", "0 đ", "👤 Khách vãng lai",  "#f0fdf4", "#16a34a"),
            ("Doanh thu thuê bao", "0 đ", "💳 Thuê bao tháng",  "#faf5ff", "#9333ea"),
        ]
        for title_txt, value, sub, bg, color in metric_defs:
            card = QFrame()
            card.setStyleSheet(f"QFrame {{ background: {bg}; border: none; border-radius: 12px; }}")
            card.setMinimumHeight(100)
            cl = QVBoxLayout(card); cl.setContentsMargins(18, 16, 18, 16); cl.setSpacing(4)

            t_lbl = label(title_txt)
            t_lbl.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
            cl.addWidget(t_lbl)

            v_lbl = label(value, bold=True)
            v_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 800; background: transparent;")
            cl.addWidget(v_lbl)

            s_lbl = label(sub)
            s_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600; background: transparent;")
            cl.addWidget(s_lbl)

            cards_row.addWidget(card, 1)
        box.addLayout(cards_row)

        # ── Chart row 1: Doanh thu theo giờ (2fr) | Phân loại xe (1fr) ─
        charts_row1 = QHBoxLayout(); charts_row1.setSpacing(14)

        # Left: Doanh thu theo giờ line chart
        rev_panel = QFrame(); rev_panel.setObjectName("panel")
        rev_lay = QVBoxLayout(rev_panel); rev_lay.setContentsMargins(18, 16, 18, 12); rev_lay.setSpacing(8)

        rev_hdr = QHBoxLayout()
        rev_title = label("📈 Doanh thu theo giờ", bold=True)
        rev_title.setStyleSheet("font-size: 14px; color: #0f172a;")
        rev_hdr.addWidget(rev_title); rev_hdr.addStretch()

        # Cột / Đường toggle
        toggle_box = QFrame(); toggle_box.setStyleSheet("background: #f1f5f9; border-radius: 6px; border: none;")
        tg_lay = QHBoxLayout(toggle_box); tg_lay.setContentsMargins(2, 2, 2, 2); tg_lay.setSpacing(2)
        btn_col = QPushButton("Cột"); btn_col.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_col.setStyleSheet("QPushButton { background: #64748b; color: white; border: none; border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: 700; }")
        btn_line = QPushButton("Đường"); btn_line.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_line.setStyleSheet("QPushButton { background: transparent; color: #64748b; border: none; padding: 3px 10px; font-size: 11px; font-weight: 600; }")
        tg_lay.addWidget(btn_col); tg_lay.addWidget(btn_line)
        rev_hdr.addWidget(toggle_box)
        rev_lay.addLayout(rev_hdr)

        # Inline grid chart (like dashboard, not QtCharts – avoids rendering issues)
        rev_chart_frame = QFrame()
        rev_chart_frame.setStyleSheet("background: white; border: none; border-radius: 6px;")
        rev_chart_frame.setMinimumHeight(200)
        rev_grid = QGridLayout(rev_chart_frame); rev_grid.setContentsMargins(4, 4, 4, 2); rev_grid.setSpacing(0)
        rows_count = 6
        for r, v in enumerate(range(rows_count, -1, -1)):
            y_lbl = label(str(v))
            y_lbl.setStyleSheet("color: #94a3b8; font-size: 9px;")
            y_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            y_lbl.setFixedWidth(24)
            rev_grid.addWidget(y_lbl, r, 0)
            grid_line = QFrame(); grid_line.setFrameShape(QFrame.Shape.HLine)
            grid_line.setStyleSheet("border: none; border-top: 1px solid #f1f5f9;")
            rev_grid.addWidget(grid_line, r, 1)
            rev_grid.setRowStretch(r, 1)
        hour_row = QHBoxLayout(); hour_row.setSpacing(0)
        for h in range(24):
            h_lbl = label(f"{h:02d}:00")
            h_lbl.setStyleSheet("color: #94a3b8; font-size: 8px;")
            h_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hour_row.addWidget(h_lbl, 1)
        rev_grid.addLayout(hour_row, rows_count + 1, 1)
        rev_grid.setColumnStretch(1, 1)
        rev_lay.addWidget(rev_chart_frame, 1)
        charts_row1.addWidget(rev_panel, 2)

        # Right: Phân loại xe pie chart
        pie_panel = QFrame(); pie_panel.setObjectName("panel")
        pie_lay = QVBoxLayout(pie_panel); pie_lay.setContentsMargins(18, 16, 18, 12); pie_lay.setSpacing(8)
        pie_title = label("🥧 Phân loại xe", bold=True)
        pie_title.setStyleSheet("font-size: 14px; color: #0f172a;")
        pie_lay.addWidget(pie_title)

        self.pie_chart = QChart()
        self.pie_chart.setMargins(QMargins(0, 0, 0, 0))
        self.pie_chart.setBackgroundBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.pie_chart.legend().setFont(QFont("Segoe UI", 10))

        self.pseries = QPieSeries()
        self.slice_xm = QPieSlice("Xe máy", 1)
        self.slice_xm.setColor(QColor("#f97316"))
        self.slice_xm.setLabelVisible(False)
        self.pseries.append(self.slice_xm)
        self.pie_chart.addSeries(self.pseries)

        self.pie_view = QChartView(self.pie_chart)
        self.pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.pie_view.setStyleSheet("border: none; background: transparent;")
        self.pie_view.setMinimumHeight(200)
        pie_lay.addWidget(self.pie_view, 1)
        charts_row1.addWidget(pie_panel, 1)

        box.addLayout(charts_row1)

        # ── Chart row 2: Lưu lượng xe (2fr) | Thanh toán (1fr) ─────────
        charts_row2 = QHBoxLayout(); charts_row2.setSpacing(14)

        # Left: Lưu lượng xe theo giờ — area chart using QtCharts
        flow_panel = QFrame(); flow_panel.setObjectName("panel")
        flow_lay = QVBoxLayout(flow_panel); flow_lay.setContentsMargins(18, 16, 18, 12); flow_lay.setSpacing(8)
        flow_title = label("🌊 Lưu lượng xe theo giờ", bold=True)
        flow_title.setStyleSheet("font-size: 14px; color: #0f172a;")
        flow_lay.addWidget(flow_title)

        self.flow_chart = QChart()
        self.flow_chart.setMargins(QMargins(0, 0, 0, 0))
        self.flow_chart.setBackgroundBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.flow_chart.legend().hide()

        self.fseries = QLineSeries()
        data_points = [(0,0),(1,0),(2,0),(3,1.2),(4,0.5),(5,0),(6,0),(7,0),(8,0),(9,0),
                       (10,0),(11,0),(12,0),(13,0),(14,0),(15,0),(16,0),(17,0),(18,0),(19,0),
                       (20,0),(21,0),(22,0),(23,0)]
        for x, y in data_points:
            self.fseries.append(x, y)
        fpen = QPen(QColor("#3b82f6")); fpen.setWidth(2); self.fseries.setPen(fpen)

        self.flow_area = QAreaSeries(self.fseries)
        area_pen = QPen(QColor("#3b82f6")); area_pen.setWidth(2); self.flow_area.setPen(area_pen)
        self.flow_area.setBrush(QBrush(QColor(59, 130, 246, 40)))

        self.flow_chart.addSeries(self.flow_area)

        self.f_ax_x = QValueAxis(); self.f_ax_x.setRange(0, 23); self.f_ax_x.setTickCount(13)
        self.f_ax_x.setLabelFormat("%d:00"); self.f_ax_x.setLabelsFont(QFont("Segoe UI", 8))
        self.f_ax_x.setGridLineColor(QColor("#f1f5f9")); self.f_ax_x.setLinePenColor(QColor("#e2e8f0"))

        self.f_ax_y = QValueAxis(); self.f_ax_y.setRange(0, 2); self.f_ax_y.setTickCount(5)
        self.f_ax_y.setLabelsFont(QFont("Segoe UI", 8))
        self.f_ax_y.setGridLineColor(QColor("#f1f5f9")); self.f_ax_y.setLinePenColor(QColor("#e2e8f0"))

        self.flow_chart.addAxis(self.f_ax_x, Qt.AlignmentFlag.AlignBottom)
        self.flow_chart.addAxis(self.f_ax_y, Qt.AlignmentFlag.AlignLeft)
        self.flow_area.attachAxis(self.f_ax_x); self.flow_area.attachAxis(self.f_ax_y)

        self.flow_view = QChartView(self.flow_chart)
        self.flow_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.flow_view.setStyleSheet("border: none; background: transparent;")
        self.flow_view.setMinimumHeight(180)
        flow_lay.addWidget(self.flow_view, 1)
        charts_row2.addWidget(flow_panel, 2)

        # Right: Hình thức thanh toán
        pay_panel = QFrame(); pay_panel.setObjectName("panel")
        pay_lay = QVBoxLayout(pay_panel); pay_lay.setContentsMargins(18, 16, 18, 16); pay_lay.setSpacing(12)
        pay_title = label("💳 Hình thức thanh toán", bold=True)
        pay_title.setStyleSheet("font-size: 14px; color: #0f172a;")
        pay_lay.addWidget(pay_title)

        def _payment_row(icon_text: str, icon_bg: str, icon_color: str, name: str, amount: str, pct: str, bar_color: str, bar_val: int) -> QVBoxLayout:
            row_layout = QVBoxLayout(); row_layout.setSpacing(4)
            top = QHBoxLayout()
            icon_lbl = label(icon_text)
            icon_lbl.setStyleSheet(f"background: {icon_bg}; color: {icon_color}; border-radius: 6px; padding: 4px 8px; font-size: 14px; border: none;")
            icon_lbl.setFixedSize(34, 34)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            top.addWidget(icon_lbl)
            name_lbl = label(name, bold=True)
            name_lbl.setStyleSheet("font-size: 13px; color: #0f172a;")
            top.addWidget(name_lbl)
            top.addStretch()
            val_col = QVBoxLayout(); val_col.setSpacing(0)
            a_lbl = label(amount, bold=True); a_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            a_lbl.setStyleSheet("font-size: 13px; color: #0f172a;")
            p_lbl = label(pct); p_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            p_lbl.setStyleSheet("font-size: 10px; color: #64748b;")
            val_col.addWidget(a_lbl); val_col.addWidget(p_lbl)
            top.addLayout(val_col)
            row_layout.addLayout(top)
            prog = QProgressBar(); prog.setValue(bar_val); prog.setFixedHeight(6); prog.setTextVisible(False)
            prog.setStyleSheet(f"QProgressBar {{ border: none; background: #e2e8f0; border-radius: 3px; }} QProgressBar::chunk {{ background: {bar_color}; border-radius: 3px; }}")
            row_layout.addWidget(prog)
            return row_layout

        pay_lay.addLayout(_payment_row("💵", "#dcfce7", "#16a34a", "Tiền mặt",     "0 đ", "0%",   "#16a34a", 0))

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("border: none; border-top: 1px solid #f1f5f9;")
        pay_lay.addWidget(sep2)

        pay_lay.addLayout(_payment_row("💳", "#eff6ff", "#3b82f6", "Chuyển khoản", "0 đ", "0%",   "#3b82f6", 0))

        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("border: none; border-top: 1px solid #f1f5f9;")
        pay_lay.addWidget(sep3)

        pay_lay.addLayout(_payment_row("🏷", "#faf5ff", "#9333ea", "Thuê bao",      "0 đ", "0%",   "#9333ea", 0))

        pay_lay.addStretch()
        charts_row2.addWidget(pay_panel, 1)

        box.addLayout(charts_row2)

        return page
