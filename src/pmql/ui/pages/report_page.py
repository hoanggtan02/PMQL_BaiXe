from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QPieSeries, QPieSlice, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
from pmql.ui.components import *

class ReportPageMixin:
    def reports_page(self) -> QWidget:
        page = QWidget(); page.setObjectName("page")
        page.setStyleSheet("QWidget#page { background: #f8fafc; }")
        layout = QVBoxLayout(page); layout.setContentsMargins(28, 20, 28, 28); layout.setSpacing(20)

        # Header with title and time filters
        header_row = QHBoxLayout()
        title_box = QVBoxLayout(); title_box.setSpacing(4)
        title = label("Khoảng thời gian", "muted"); title.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        title_box.addWidget(title)
        
        filter_row = QHBoxLayout(); filter_row.setSpacing(8)
        btn_today = QPushButton("Hôm nay"); btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_today.setStyleSheet("QPushButton { background: #f97316; color: white; border: none; border-radius: 16px; padding: 6px 16px; font-weight: 600; }")
        filter_row.addWidget(btn_today)
        
        for text in ["7 ngày", "Tháng này", "Tùy chọn"]:
            btn = QPushButton(text); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background: white; color: #475569; border: 1px solid #cbd5e1; border-radius: 16px; padding: 6px 16px; font-weight: 600; }")
            filter_row.addWidget(btn)
        
        title_box.addLayout(filter_row)
        header_row.addLayout(title_box)
        header_row.addStretch()
        
        # Actions: Xem báo cáo, Xuất
        actions_row = QHBoxLayout(); actions_row.setAlignment(Qt.AlignmentFlag.AlignBottom)
        view_btn = QPushButton("🔍 Xem báo cáo"); view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.setStyleSheet("QPushButton { background: #f97316; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; } QPushButton:hover { background: #ea580c; }")
        export_btn = QPushButton("📥 Xuất ▾"); export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet("QPushButton { background: white; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 16px; font-weight: bold; }")
        actions_row.addWidget(view_btn); actions_row.addWidget(export_btn)
        header_row.addLayout(actions_row)
        
        layout.addLayout(header_row)

        # 4 Metric Cards
        cards_layout = QHBoxLayout(); cards_layout.setSpacing(16)
        metrics = [
            ("Tổng doanh thu", "0 đ", "💵 Đã thu", "#fff7ed", "#ea580c"),
            ("Tổng lượt gửi", "1", "🚗 Xe hoàn thành", "#f0fdf4", "#3b82f6"),
            ("Doanh thu vãng lai", "0 đ", "👤 Khách vãng lai", "#f0fdf4", "#16a34a"),
            ("Doanh thu thuê bao", "0 đ", "💳 Thuê bao tháng", "#faf5ff", "#9333ea")
        ]
        for title, value, sub, bg, color in metrics:
            card = QFrame(); card.setStyleSheet(f"QFrame {{ background: {bg}; border: 1px solid #e2e8f0; border-radius: 8px; }}")
            card_lay = QVBoxLayout(card); card_lay.setContentsMargins(16, 16, 16, 16); card_lay.setSpacing(4)
            t_lbl = label(title); t_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            v_lbl = label(value, bold=True); v_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 800; border: none;")
            s_lbl = label(sub); s_lbl.setStyleSheet(f"color: {color}; font-size: 11px; border: none;")
            card_lay.addWidget(t_lbl); card_lay.addWidget(v_lbl); card_lay.addWidget(s_lbl)
            cards_layout.addWidget(card)
        layout.addLayout(cards_layout)

        # Main Charts Area
        charts_layout = QGridLayout(); charts_layout.setSpacing(16)
        
        # 1. Doanh thu theo giờ (Line Chart)
        rev_frame = QFrame(); rev_frame.setStyleSheet("QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        rev_lay = QVBoxLayout(rev_frame); rev_lay.setContentsMargins(16, 16, 16, 16)
        rev_header = QHBoxLayout()
        rev_title = label("📈 Doanh thu theo giờ", bold=True); rev_title.setStyleSheet("color: #f97316; font-size: 14px; border: none;")
        rev_header.addWidget(rev_title); rev_header.addStretch()
        
        rev_chart = QChart(); rev_chart.legend().hide(); rev_chart.setMargins(QMargins(0,0,0,0))
        series = QLineSeries(); series.append(0, 0); series.append(23, 0)
        pen = QPen(QColor("#f97316")); pen.setWidth(2); series.setPen(pen)
        rev_chart.addSeries(series)
        axis_x = QValueAxis(); axis_x.setRange(0, 23); axis_x.setTickCount(24); axis_x.setLabelFormat("%d:00")
        axis_y = QValueAxis(); axis_y.setRange(0, 1); axis_y.setTickCount(6)
        rev_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom); rev_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_x); series.attachAxis(axis_y)
        
        rev_view = QChartView(rev_chart); rev_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        rev_view.setStyleSheet("border: none; background: transparent;")
        rev_lay.addLayout(rev_header); rev_lay.addWidget(rev_view)
        charts_layout.addWidget(rev_frame, 0, 0, 1, 2)
        
        # 2. Phân loại xe (Pie Chart)
        pie_frame = QFrame(); pie_frame.setStyleSheet("QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        pie_lay = QVBoxLayout(pie_frame); pie_lay.setContentsMargins(16, 16, 16, 16)
        pie_title = label("🥧 Phân loại xe", bold=True); pie_title.setStyleSheet("color: #f97316; font-size: 14px; border: none;")
        pie_lay.addWidget(pie_title)
        
        pie_chart = QChart(); pie_chart.setMargins(QMargins(0,0,0,0)); pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        pseries = QPieSeries()
        slice_xm = QPieSlice("Xe máy", 1); slice_xm.setColor(QColor("#f97316"))
        pseries.append(slice_xm)
        pie_chart.addSeries(pseries)
        
        pie_view = QChartView(pie_chart); pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        pie_view.setStyleSheet("border: none; background: transparent;")
        pie_lay.addWidget(pie_view)
        charts_layout.addWidget(pie_frame, 0, 2, 1, 1)

        # 3. Lưu lượng xe theo giờ (Line Chart)
        flow_frame = QFrame(); flow_frame.setStyleSheet("QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        flow_lay = QVBoxLayout(flow_frame); flow_lay.setContentsMargins(16, 16, 16, 16)
        flow_title = label("🌊 Lưu lượng xe theo giờ", bold=True); flow_title.setStyleSheet("color: #f97316; font-size: 14px; border: none;")
        flow_lay.addWidget(flow_title)
        
        flow_chart = QChart(); flow_chart.legend().hide(); flow_chart.setMargins(QMargins(0,0,0,0))
        fseries = QLineSeries(); fseries.append(0, 0); fseries.append(2, 0); fseries.append(3, 1); fseries.append(4, 0); fseries.append(23, 0)
        fpen = QPen(QColor("#3b82f6")); fpen.setWidth(2); fseries.setPen(fpen)
        flow_chart.addSeries(fseries)
        f_axis_x = QValueAxis(); f_axis_x.setRange(0, 23); f_axis_x.setTickCount(24)
        f_axis_y = QValueAxis(); f_axis_y.setRange(0, 1); f_axis_y.setTickCount(6)
        flow_chart.addAxis(f_axis_x, Qt.AlignmentFlag.AlignBottom); flow_chart.addAxis(f_axis_y, Qt.AlignmentFlag.AlignLeft)
        fseries.attachAxis(f_axis_x); fseries.attachAxis(f_axis_y)
        
        flow_view = QChartView(flow_chart); flow_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        flow_view.setStyleSheet("border: none; background: transparent;")
        flow_lay.addWidget(flow_view)
        charts_layout.addWidget(flow_frame, 1, 0, 1, 2)
        
        # 4. Hình thức thanh toán
        pay_frame = QFrame(); pay_frame.setStyleSheet("QFrame { background: white; border: 1px solid #e2e8f0; border-radius: 8px; }")
        pay_lay = QVBoxLayout(pay_frame); pay_lay.setContentsMargins(16, 16, 16, 16)
        pay_title = label("💳 Hình thức thanh toán", bold=True); pay_title.setStyleSheet("color: #f97316; font-size: 14px; border: none;")
        pay_lay.addWidget(pay_title)
        
        pay_row = QHBoxLayout()
        pay_icon = label("💵"); pay_icon.setStyleSheet("background: #dcfce7; color: #16a34a; border-radius: 4px; padding: 4px;")
        pay_row.addWidget(pay_icon)
        pay_row.addWidget(label("Tiền mặt", bold=True))
        pay_row.addStretch()
        pay_val = QVBoxLayout(); pay_val.setSpacing(0)
        val1 = label("0 đ", bold=True); val1.setAlignment(Qt.AlignmentFlag.AlignRight)
        val2 = label("0%"); val2.setAlignment(Qt.AlignmentFlag.AlignRight); val2.setStyleSheet("color: #64748b; font-size: 10px;")
        pay_val.addWidget(val1); pay_val.addWidget(val2)
        pay_row.addLayout(pay_val)
        pay_lay.addLayout(pay_row)
        
        # Progress bar mock
        prog = QProgressBar(); prog.setValue(0); prog.setFixedHeight(8)
        prog.setStyleSheet("QProgressBar { border: none; background: #e2e8f0; border-radius: 4px; } QProgressBar::chunk { background: #16a34a; border-radius: 4px; }")
        prog.setTextVisible(False)
        pay_lay.addWidget(prog)
        pay_lay.addStretch()
        
        charts_layout.addWidget(pay_frame, 1, 2, 1, 1)

        layout.addLayout(charts_layout)
        return page
