from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pmql.ui.components import *
from pmql.ui.db_helpers import *
import asyncio
from datetime import date, datetime, timedelta

class DashboardPageMixin:
    def overview_page(self) -> QWidget:
            page, box = self.page()
            box.setContentsMargins(24, 20, 24, 20)
            box.setSpacing(16)
    
            # ── Metric cards row ──────────────────────────────────────
            cards_row = QHBoxLayout(); cards_row.setSpacing(12)
            metric_defs = [
                ("Xe đang trong bãi", "2", "0% công suất (60 chỗ giới hạn chỗ)", "🚙", "#2563eb"),
                ("Lượt vào hôm nay", "0", "Ra: 0", "↪", "#16a34a"),
                ("Doanh thu hôm nay", "0 đ", "Tháng: 0 đ", "💵", "#ea580c"),
                ("Cảnh báo chờ xử lý", "0", "Xem và xử lý →", "⚠", "#dc2626"),
            ]
            self.overview_values = []
            self.overview_sub_labels = []
            for title_txt, init_val, subtitle, icon, bg in metric_defs:
                card = QFrame()
                card.setStyleSheet(f"QFrame {{ background: {bg}; border-radius: 12px; border: none; }}")
                card.setMinimumHeight(142)
                card_box = QVBoxLayout(card); card_box.setContentsMargins(18, 16, 18, 16); card_box.setSpacing(4)
                top_row = QHBoxLayout()
                ttl = label(title_txt)
                ttl.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 12px; font-weight: 600;")
                top_row.addWidget(ttl); top_row.addStretch()
                icon_lbl = label(icon)
                icon_lbl.setStyleSheet("color: rgba(255,255,255,0.30); font-size: 28px;")
                top_row.addWidget(icon_lbl)
                card_box.addLayout(top_row)
                val_lbl = label(init_val, bold=True)
                val_lbl.setStyleSheet("color: white; font-size: 30px; font-weight: 800;")
                card_box.addWidget(val_lbl)
                # progress bar for first card
                if title_txt == "Xe đang trong bãi":
                    prog = QProgressBar(); prog.setRange(0, 60); prog.setValue(2)
                    prog.setFixedHeight(6)
                    prog.setStyleSheet(f"QProgressBar {{ background: rgba(255,255,255,0.25); border: none; border-radius: 3px; }} QProgressBar::chunk {{ background: white; border-radius: 3px; }}")
                    card_box.addWidget(prog)
                    self.overview_progress = prog
                sub_lbl = label(subtitle)
                sub_lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px;")
                card_box.addWidget(sub_lbl)
                self.overview_values.append(val_lbl)
                self.overview_sub_labels.append(sub_lbl)
                cards_row.addWidget(card, 1)
            box.addLayout(cards_row)
    
            # ── Middle row: Lane status  |  Revenue chart ────────────
            mid_row = QHBoxLayout(); mid_row.setSpacing(12)
    
            # Left: Lane status panel
            lane_panel = QFrame(); lane_panel.setObjectName("panel")
            lane_layout = QVBoxLayout(lane_panel); lane_layout.setContentsMargins(16, 14, 16, 14); lane_layout.setSpacing(8)
            lane_header = QHBoxLayout()
            lane_title_lbl = label("🚦 Trạng thái làn xe", bold=True)
            lane_title_lbl.setStyleSheet("font-size: 14px;")
            lane_header.addWidget(lane_title_lbl); lane_header.addStretch()
            refresh_icon = icon_btn("fa5s.sync-alt", "", _BTN_PLAIN_STYLE, 14)
            refresh_icon.setFixedSize(30, 30)
            refresh_icon.clicked.connect(self.refresh_live)
            operate_btn = QPushButton("Vận hành")
            operate_btn.setObjectName("primary")
            operate_btn.setStyleSheet("QPushButton { padding: 6px 16px; font-weight: 700; }")
            operate_btn.clicked.connect(lambda: self.go("operations"))
            lane_header.addWidget(refresh_icon); lane_header.addWidget(operate_btn)
            lane_layout.addLayout(lane_header)
    
            self.overview_lane_rows = []
            try: lanes_data = asyncio.run(_lanes(self.settings))
            except Exception: lanes_data = []
            for lane in lanes_data:
                row_w = QFrame()
                row_w.setStyleSheet("QFrame { background: #ffffff; border-radius: 8px; border: none; }")
                row_lay = QHBoxLayout(row_w); row_lay.setContentsMargins(12, 8, 12, 8); row_lay.setSpacing(10)
                # direction arrow
                arrow = "→" if lane.direction == "IN" else ("←" if lane.direction == "OUT" else "⇄")
                arrow_lbl = label(arrow)
                arrow_color = "#16a34a" if lane.direction == "IN" else ("#dc2626" if lane.direction == "OUT" else "#ea580c")
                arrow_lbl.setStyleSheet(f"color: {arrow_color}; font-size: 18px; font-weight: bold;")
                arrow_lbl.setFixedWidth(24)
                row_lay.addWidget(arrow_lbl)
                info_col = QVBoxLayout(); info_col.setSpacing(1)
                name_lbl = label(lane.name, bold=True)
                name_lbl.setStyleSheet("font-size: 13px;")
                sub_lbl2 = label("0 xe • 4 thiết bị")
                sub_lbl2.setStyleSheet("color: #64748b; font-size: 11px;")
                info_col.addWidget(name_lbl); info_col.addWidget(sub_lbl2)
                row_lay.addLayout(info_col, 1)
                status_badge = label("Chờ xe", "badge")
                status_badge.setStyleSheet("background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; border-radius: 10px; padding: 3px 10px; font-size: 11px;")
                row_lay.addWidget(status_badge)
                lane_layout.addWidget(row_w)
                if lane != lanes_data[-1]:
                    sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                    sep.setStyleSheet("border: none; border-top: 1px solid #f1f5f9;")
                    lane_layout.addWidget(sep)
                self.overview_lane_rows.append((sub_lbl2, status_badge))
            if not lanes_data:
                lane_layout.addWidget(label("Chưa có làn hoạt động.", "muted"))
            lane_layout.addStretch()
            mid_row.addWidget(lane_panel, 2)
    
            # Right: Revenue chart (placeholder)
            chart_panel = QFrame(); chart_panel.setObjectName("panel")
            chart_layout = QVBoxLayout(chart_panel); chart_layout.setContentsMargins(16, 14, 16, 14); chart_layout.setSpacing(8)
            chart_header = QHBoxLayout()
            chart_title = label("◱  Doanh thu theo giờ", bold=True)
            chart_title.setStyleSheet("font-size: 14px;")
            chart_header.addWidget(chart_title); chart_header.addStretch()
            btn_day = QPushButton("Hôm nay")
            btn_day.setStyleSheet("background: #64748b; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            btn_week = QPushButton("Tuần")
            btn_week.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            def set_chart_period(period: str) -> None:
                active, inactive = (btn_day, btn_week) if period == "day" else (btn_week, btn_day)
                active.setStyleSheet("background: #64748b; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
                inactive.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            btn_day.clicked.connect(lambda: set_chart_period("day"))
            btn_week.clicked.connect(lambda: set_chart_period("week"))
            chart_header.addWidget(btn_day); chart_header.addWidget(btn_week)
            chart_layout.addLayout(chart_header)
    
            # A lightweight grid keeps the revenue scale understandable before data is present.
            chart_area = QFrame()
            chart_area.setStyleSheet("background: white; border-radius: 8px; border: none;")
            chart_area.setMinimumHeight(245)
            chart_inner = QGridLayout(chart_area); chart_inner.setContentsMargins(6, 6, 6, 2); chart_inner.setSpacing(0)
            for row, value in enumerate(range(10, -1, -1)):
                y_label = label("1" if value == 10 else ("0" if value == 0 else f"0.{value}"))
                y_label.setStyleSheet("color: #64748b; font-size: 9px;")
                y_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                chart_inner.addWidget(y_label, row, 0)
                line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet("border: none; border-top: 1px solid #e2e8f0;")
                chart_inner.addWidget(line, row, 1)
                chart_inner.setRowStretch(row, 1)
            hour_row = QHBoxLayout(); hour_row.setSpacing(0)
            for h in range(24):
                h_lbl = label(f"{h}h")
                h_lbl.setStyleSheet("color: #94a3b8; font-size: 9px;")
                h_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                hour_row.addWidget(h_lbl, 1)
            chart_inner.addLayout(hour_row, 11, 1)
            chart_inner.setColumnStretch(1, 1)
            chart_layout.addWidget(chart_area, 1)
            mid_row.addWidget(chart_panel, 3)
            box.addLayout(mid_row)
    
            # ── Bottom row: Active vehicles table  |  Breakdown + stats ─
            bot_row = QHBoxLayout(); bot_row.setSpacing(12)
    
            # Left: Active vehicles table
            veh_panel = QFrame(); veh_panel.setObjectName("panel")
            veh_layout = QVBoxLayout(veh_panel); veh_layout.setContentsMargins(16, 14, 16, 14); veh_layout.setSpacing(8)
            veh_header = QHBoxLayout()
            veh_title = label("🚗 Xe đang trong bãi", bold=True)
            veh_title.setStyleSheet("font-size: 14px;")
            veh_header.addWidget(veh_title); veh_header.addStretch()
            see_all_btn = QPushButton("Xem tất cả")
            see_all_btn.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 12px; font-size: 12px;")
            see_all_btn.clicked.connect(lambda: self.go("sessions"))
            veh_header.addWidget(see_all_btn)
            veh_layout.addLayout(veh_header)
    
            self.live_table = QTableWidget(0, 6)
            self.live_table.setHorizontalHeaderLabels(["BIỂN SỐ", "LOẠI XE", "VÀO LÚC", "THỜI GIAN", "LOẠI", "LÀN"])
            self.live_table.setAlternatingRowColors(True)
            self.live_table.setShowGrid(False)
            self.live_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.live_table.verticalHeader().setVisible(False)
            self.live_table.setMinimumHeight(160)
            self.live_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            hdr = self.live_table.horizontalHeader()
            for i in range(6): hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            self.live_table.setStyleSheet(
                "QTableWidget { border: 1px solid #e2e8f0; background: white; border-radius: 8px; }"
                "QHeaderView::section { background: #f8fafc; color: #64748b; font-size: 10px; font-weight: 700; border: none; border-bottom: 1px solid #e2e8f0; padding: 8px; }"
                "QTableWidget::item { padding: 8px 4px; border-bottom: 1px solid #f8fafc; }"
            )
            veh_layout.addWidget(self.live_table, 1)
            bot_row.addWidget(veh_panel, 2)
    
            # Right: Vehicle type breakdown + quick stats
            right_col = QVBoxLayout(); right_col.setSpacing(12)
    
            # Phân loại xe hôm nay
            breakdown_panel = QFrame(); breakdown_panel.setObjectName("panel")
            breakdown_layout = QVBoxLayout(breakdown_panel); breakdown_layout.setContentsMargins(16, 14, 16, 14); breakdown_layout.setSpacing(8)
            breakdown_title = label("🏍 Phân loại xe hôm nay", bold=True)
            breakdown_title.setStyleSheet("font-size: 14px;")
            breakdown_layout.addWidget(breakdown_title)
            self.overview_breakdown_lbl = label("Chưa có dữ liệu hôm nay.", "muted")
            self.overview_breakdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.overview_breakdown_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 20px;")
            breakdown_layout.addWidget(self.overview_breakdown_lbl, 1)
            right_col.addWidget(breakdown_panel, 1)
    
            # Thống kê nhanh
            stats_panel = QFrame(); stats_panel.setObjectName("panel")
            stats_layout = QVBoxLayout(stats_panel); stats_layout.setContentsMargins(16, 14, 16, 14); stats_layout.setSpacing(6)
            stats_title = label("⚡ Thống kê nhanh", bold=True)
            stats_title.setStyleSheet("font-size: 14px;")
            stats_layout.addWidget(stats_title)
    
            stat_defs = [
                ("👥 Thuê bao đang gửi",   "0"),
                ("🧑 Vãng lai đang gửi",   "0"),
                ("🚦 Làn đang hoạt động",   "0 / 0"),
                ("📡 Thiết bị online",      "0 / 0"),
            ]
            self.overview_stat_lbls = []
            for stat_text, init_val in stat_defs:
                stat_row = QHBoxLayout()
                stat_name = label(stat_text)
                stat_name.setStyleSheet("color: #475569; font-size: 12px;")
                stat_val = label(init_val, bold=True)
                stat_val.setStyleSheet("font-size: 13px; color: #0f172a;")
                stat_row.addWidget(stat_name); stat_row.addStretch(); stat_row.addWidget(stat_val)
                stats_layout.addLayout(stat_row)
                self.overview_stat_lbls.append(stat_val)
                # separator
                sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("border: none; border-top: 1px solid #f1f5f9;")
                stats_layout.addWidget(sep)
            right_col.addWidget(stats_panel)
            bot_row.addLayout(right_col, 1)
            box.addLayout(bot_row)
            return page

