"""
Dashboard Widget — Bảng báo cáo phân tích lộ trình chi tiết.

THAY ĐỔI so với phiên bản cũ:
  - Bỏ đoạn code tính lại travel cost từ cost_matrix bên trong widget.
    Lý do: Dashboard không giữ tham chiếu đến cost_matrix nữa (đã là numpy).
    Toàn bộ route_costs được tính sẵn và truyền vào từ main_window._on_finished().
  - Phần hiển thị thời gian (ETA) chỉ dùng time_windows đã được truyền vào, 
    không tự tính lại travel_time (tránh phụ thuộc vào cost_matrix).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QFrame, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class DashboardWidget(QWidget):
    """Trang hiển thị báo cáo & số liệu sau khi hoàn thành chạy thuật toán."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_results = None
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # ── Header ────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_lbl = QLabel("📊 BÁO CÁO PHÂN TÍCH HIỆU SUẤT (DASHBOARD)")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet("color: #a6e3a1; margin-bottom: 5px;")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_export = QPushButton("📥 Xuất Báo cáo CSV")
        self.btn_export.setFixedWidth(180)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #94e2d5; color: #11111b;
                border-radius: 6px; font-weight: bold; padding: 8px;
            }
            QPushButton:hover { background-color: #89dceb; }
        """)
        self.btn_export.clicked.connect(self._on_export_clicked)

        header_layout.addWidget(header_lbl, stretch=1)
        header_layout.addWidget(self.btn_export)
        layout.addLayout(header_layout)

        # ── KPI Cards ─────────────────────────────────────────────────
        kpi_group = QGroupBox("📍 Chỉ số Tối ưu Tổng quan")
        kpi_group.setStyleSheet(self._group_style())
        kpi_layout = QHBoxLayout(kpi_group)
        kpi_layout.setSpacing(15)

        self.val_cost     = self._create_kpi_card(kpi_layout, "Objective tối ưu",      "—", "#f38ba8")
        self.val_vehicles = self._create_kpi_card(kpi_layout, "Số lượng xe triển khai",   "—", "#fab387")
        self.val_gen      = self._create_kpi_card(kpi_layout, "Thế hệ đạt đỉnh",          "—", "#89b4fa")
        self.val_stops    = self._create_kpi_card(kpi_layout, "Tổng số điểm giao",         "—", "#cba6f7")
        layout.addWidget(kpi_group)

        # ── Bảng chi tiết ─────────────────────────────────────────────
        table_group = QGroupBox("🚚 Phân rã lịch trình chi tiết (Vehicle Breakdown)")
        table_group.setStyleSheet(self._group_style())
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Mã số Xe", "Số điểm", "Đóng góp Phí",
            "Tải trọng (Tấn/Kg)", "Trình tự di chuyển",
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.table.setStyleSheet(self._table_style())
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table_layout.addWidget(self.table)
        layout.addWidget(table_group, stretch=1)

        # ── AI Alerts ─────────────────────────────────────────────────
        alert_group = QGroupBox("🤖 Trợ lý Phân tích AI - Cảnh báo Rủi ro")
        alert_group.setStyleSheet(self._group_style())
        self.alert_layout = QVBoxLayout(alert_group)
        self.alert_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(alert_group)

    # ------------------------------------------------------------------
    def _create_kpi_card(self, parent_layout, title: str, value: str, color: str) -> QLabel:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            f"background-color: #313244; border-radius: 8px; border-left: 5px solid {color};"
        )
        v_layout = QVBoxLayout(card)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #a6adc8; font-size: 13px; font-weight: bold;")
        v_layout.addWidget(t_lbl)

        v_lbl = QLabel(value)
        v_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        v_lbl.setStyleSheet(f"color: {color};")
        v_layout.addWidget(v_lbl)

        parent_layout.addWidget(card)
        return v_lbl

    # ------------------------------------------------------------------
    def update_dashboard(
        self,
        cost: float,
        num_vehicles: int,
        gen: int,
        num_stops: int,
        routes: list,
        route_costs: list = None,
        route_loads: list = None,
        max_capacity: int = 1,
        time_windows: dict = None,
        service_times: dict = None,
        use_tw: bool = False,
        use_capacity: bool = False,
    ):
        """
        Cập nhật dữ liệu lên UI báo cáo.

        route_costs và route_loads được tính sẵn từ main_window và truyền vào —
        Dashboard không tự tính lại để tránh phụ thuộc vào cost_matrix.
        """
        self._last_results = {
            "cost": cost, "num_vehicles": num_vehicles, "gen": gen,
            "num_stops": num_stops, "routes": routes,
            "route_costs": route_costs, "route_loads": route_loads,
        }

        # KPI
        self.val_cost.setText(f"{cost:,.1f}")
        self.val_vehicles.setText(str(num_vehicles))
        self.val_gen.setText(str(gen))
        self.val_stops.setText(str(num_stops))

        # Bảng chi tiết
        self.table.setRowCount(len(routes))
        for i, route in enumerate(routes):
            # Mã xe
            item_id = QTableWidgetItem(f"Xe {i + 1}")
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_id.setForeground(QColor("#89b4fa"))

            # Số điểm dừng
            stops = len(route) - 2
            item_stops = QTableWidgetItem(str(stops))
            item_stops.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Chi phí (đã tính sẵn từ bên ngoài)
            rcost_str = f"{route_costs[i]:,.1f}" if route_costs else "N/A"
            item_dist = QTableWidgetItem(rcost_str)
            item_dist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Tải trọng
            load_val = route_loads[i] if route_loads else 0
            overload = max(0, load_val - max_capacity) if use_capacity else 0
            rload_str = (
                f"⚠️ {load_val} / {max_capacity} (+{overload} kg)"
                if overload > 0
                else f"{load_val} / {max_capacity}"
            )
            item_load = QTableWidgetItem(rload_str)
            item_load.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if overload > 0:
                item_load.setForeground(QColor("#f38ba8"))
            elif load_val == 0:
                item_load.setForeground(QColor("#a6adc8"))

            # Trình tự di chuyển (kèm khung giờ TW nếu bật)
            route_labels = []
            for j, city in enumerate(route):
                tw_info = ""
                if use_tw and time_windows and city in time_windows:
                    ready, due = time_windows[city]
                    tw_info = (
                        f" [{ready // 60:02d}:{ready % 60:02d}"
                        f"-{due // 60:02d}:{due % 60:02d}]"
                    )
                route_labels.append(f"{city}{tw_info}")
            item_route = QTableWidgetItem(" ➔ ".join(route_labels))

            self.table.setItem(i, 0, item_id)
            self.table.setItem(i, 1, item_stops)
            self.table.setItem(i, 2, item_dist)
            self.table.setItem(i, 3, item_load)
            self.table.setItem(i, 4, item_route)

        # Xoá alerts cũ
        for i in reversed(range(self.alert_layout.count())):
            w = self.alert_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        # AI Smart Alerts
        avg_stops = num_stops / num_vehicles if num_vehicles else 0
        has_alert = False
        for i, route in enumerate(routes):
            stops = len(route) - 2
            load_val = route_loads[i] if route_loads else 0
            overload = max(0, load_val - max_capacity) if use_capacity else 0
            if overload > 0:
                has_alert = True
                warn = QLabel(
                    f"⚠️ Xe {i + 1} vượt tải {overload:,.0f} kg "
                    f"({load_val:,.0f} / {max_capacity:,.0f} kg)."
                )
                warn.setStyleSheet("color: #f38ba8; font-weight: bold;")
                warn.setWordWrap(True)
                self.alert_layout.addWidget(warn)
            if stops >= 8 and stops > avg_stops * 1.5:
                has_alert = True
                pct = int((stops / avg_stops) * 100 - 100)
                warn = QLabel(
                    f"⚠️ Tuyến Xe {i + 1} vất vả bất thường: Phải giao {stops} điểm "
                    f"(Cao hơn {pct}% so với mức trung bình). Khuyến nghị điều thêm tải!"
                )
                warn.setStyleSheet("color: #fab387; font-weight: bold;")
                warn.setWordWrap(True)
                self.alert_layout.addWidget(warn)
            elif stops == 0:
                has_alert = True
                warn = QLabel(
                    f"⚠️ Tuyến Xe {i + 1} hoàn toàn trống! "
                    f"Thuật toán dự báo xe này không cần thiết "
                    f"(Có thể giảm thông số 'Số xe')."
                )
                warn.setStyleSheet("color: #f38ba8; font-weight: bold;")
                warn.setWordWrap(True)
                self.alert_layout.addWidget(warn)

        if not has_alert:
            ok = QLabel(
                "✅ Phân bổ nhân sự/tuyến đường đồng đều. "
                "Không phát hiện rủi ro quá tải."
            )
            ok.setStyleSheet("color: #a6e3a1;")
            self.alert_layout.addWidget(ok)

    # ------------------------------------------------------------------
    def _on_export_clicked(self):
        if not self._last_results:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu để xuất!")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu Báo cáo", "VRP_Report.csv", "CSV Files (*.csv)"
        )
        if file_path:
            from utils.export_service import export_to_csv
            success = export_to_csv(
                file_path,
                self._last_results["routes"],
                self._last_results["route_costs"],
                self._last_results["route_loads"],
            )
            if success:
                QMessageBox.information(self, "Thành công",
                                        f"Đã lưu báo cáo tại:\n{file_path}")
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xuất báo cáo!")

    # ------------------------------------------------------------------
    def _group_style(self):
        return """
            QGroupBox {
                background: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 15px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px 0 5px;
            }
        """

    def _table_style(self):
        return """
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #45475a;
                padding: 5px;
            }
        """
