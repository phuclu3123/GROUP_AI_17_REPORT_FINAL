"""
Main Window — Cửa sổ chính của ứng dụng VRP-GA.

Layout:
  ┌────────────┬────────────────────────────────┐
  │            │                                │
  │  Control   │       Bản đồ Folium            │
  │  Panel     │     (QWebEngineView)           │
  │            │                                │
  │            ├────────────────────────────────┤
  │            │   Biểu đồ Convergence          │
  │            │     (Matplotlib)               │
  └────────────┴────────────────────────────────┘

THAY ĐỔI so với phiên bản cũ:
  - _load_dataset: lưu thêm `self._city_index` (Dict[str, int]) từ build_cost_matrix.
  - _on_run: truyền `cost_matrix` (numpy) và `city_index` vào GAEngine / CSOEngine.
  - _on_run: sự kiện giao thông sửa trên numpy array thay vì dict.
  - _on_finished: tính route_costs dùng numpy lookup thay vì dict.get().
  - modified_cost_matrix là bản copy của numpy array.
"""

import copy
import time
import random
import os
import tempfile
import shutil

import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QMessageBox, QTabWidget, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.control_panel import ControlPanel
from gui.map_widget import MapWidget
from gui.editor_widget import EditorWidget # THAY THẾ StaticMapWidget
from gui.chart_widget import ChartWidget
from ga_core.ga_engine import GAEngine, GAWorker
from cso_core.cso_engine import CSOEngine, CSOWorker  # MOVED
from ga_core.cost_matrix import build_cost_matrix
from ga_core.fitness import DEFAULT_CAPACITY_PENALTY_WEIGHT
from data.vrp_data import get_dataset, load_custom_data # MOVED load_custom_data
from utils.constants import DATASET_EUROPE
from gui.dashboard_widget import DashboardWidget # MOVED


class MainWindow(QMainWindow):
    """Cửa sổ chính."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧬 VRP — Genetic Algorithm Solver")
        self.setMinimumSize(1200, 750)

        # Dữ liệu hiện tại
        self._current_dataset = DATASET_EUROPE
        self._cities = self._coords = self._depots = None
        # THAY ĐỔI: cost_matrix là numpy ndarray, city_index là dict
        self._cost_matrix: np.ndarray = None
        self._city_index: dict = {}
        self._handling = self._demands = None
        self._point_counter = 0 # Bộ đếm điểm duy nhất
        self._time_windows = self._service_times = None
        self._workers = []
        self._blocked_edges = []
        self._run_started_at = None
        self._run_algorithm = ""
        self._ab_metrics = {}
        self._single_metrics = None

        self._build_ui()
        self._connect_signals()
        self._load_dataset(self._current_dataset)
        self.setStyleSheet(self._global_style())

    def __del__(self):
        """Dọn dẹp thư mục tạm khi widget bị hủy."""
        try:
            if hasattr(self, '_tmp_dir') and os.path.exists(self._tmp_dir):
                shutil.rmtree(self._tmp_dir)
        except:
            pass

    # ------------------------------------------------------------------
    def _build_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; }"
            "QTabBar::tab { font-size: 13px; font-weight: bold; padding: 8px 20px;"
            "  background: #313244; color: #a6adc8; margin-right: 2px;"
            "  border-top-left-radius: 4px; border-top-right-radius: 4px; }"
            "QTabBar::tab:selected { background: #cba6f7; color: #1e1e2e; }"
        )
        self.setCentralWidget(self.tabs)

        # ── Tab 1: Command Center ─────────────────────────────────────
        tab1_widget = QWidget()
        h_layout = QHBoxLayout(tab1_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        self.control = ControlPanel()
        h_layout.addWidget(self.control)

        self.right_tabs = QTabWidget()
        self.right_tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; }"
            "QTabBar::tab { font-size: 13px; font-weight: bold; padding: 8px 20px;"
            "  background: #313244; color: #a6adc8; margin-right: 2px;"
            "  border-top-left-radius: 4px; border-top-right-radius: 4px; }"
            "QTabBar::tab:selected { background: #89b4fa; color: #1e1e2e; }"
        )

        # Map tab
        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)
        map_layout.setContentsMargins(0, 0, 0, 0)

        map_toolbar = QHBoxLayout()
        map_toolbar.setContentsMargins(10, 5, 10, 5)
        self.btn_export_map = QPushButton("📸 Chụp ảnh Bản đồ (PNG)")
        self.btn_export_map.setStyleSheet(
            "QPushButton { background-color: #f9e2af; color: #11111b; border-radius: 4px;"
            "  font-weight: bold; padding: 5px 10px; }"
            "QPushButton:hover { background-color: #f5e0a0; }"
        )
        map_toolbar.addStretch()
        map_toolbar.addWidget(self.btn_export_map)

        self.map_widget = MapWidget()
        map_layout.addLayout(map_toolbar)
        map_layout.addWidget(self.map_widget, stretch=1)

        self.chart_widget = ChartWidget()
        self.editor_widget = EditorWidget()

        self.right_tabs.addTab(map_tab, "🗺️ Bản đồ Folium")
        self.right_tabs.addTab(self.editor_widget, "📐 Biên tập Sơ đồ")
        self.right_tabs.addTab(self.chart_widget, "📈 Biểu đồ Hội tụ")
        h_layout.addWidget(self.right_tabs, stretch=1)

        # ── Tab 2: Dashboard ──────────────────────────────────────────
        self.dashboard_widget = DashboardWidget()

        self.tabs.addTab(tab1_widget, "📍 Màn hình Điều Phối (Command Center)")
        self.tabs.addTab(self.dashboard_widget, "📊 Báo cáo Hiệu suất (Dashboard)")

        self.statusBar().showMessage("Sẵn sàng")
        self.statusBar().setStyleSheet("color:#a6adc8; font-size:11px;")

    # ------------------------------------------------------------------
    def _connect_signals(self):
        self.control.run_clicked.connect(self._on_run)
        self.control.stop_clicked.connect(self._on_stop)
        self.control.reset_clicked.connect(self._on_reset)
        self.control.dataset_changed.connect(self._load_dataset)
        self.control.customize_depots_clicked.connect(self._on_customize_depots)
        self.btn_export_map.clicked.connect(self._on_export_map)
        self.editor_widget.point_added.connect(self._on_point_added)
        self.editor_widget.map_view.point_removed.connect(self._on_point_removed)
        self.editor_widget.undo_requested.connect(self._on_undo)
        self.editor_widget.clear_requested.connect(self._on_clear_custom)

    # ------------------------------------------------------------------
    def _load_dataset(self, name: str):
        """Tải dataset → chuyển cost_matrix sang numpy."""
        self._current_dataset = name
        try:
            if os.path.exists(name) and name.endswith(".csv"):
                (self._cities, self._coords, self._depots,
                 cost_dict, self._handling, self._demands,
                 self._time_windows, self._service_times) = load_custom_data(name)
                display_name = os.path.basename(name)
            else:
                (self._cities, self._coords, self._depots,
                 cost_dict, self._handling, self._demands,
                 self._time_windows, self._service_times) = get_dataset(name)
                display_name = name

            # THÊM MỚI: cost_matrix là numpy, city_index là dict
            self._cost_matrix, self._city_index = build_cost_matrix(
                self._cities, cost_dict
            )

            self.map_widget.show_map(self._coords, self._depots)
            self.editor_widget.update_plot(self._coords, self._depots)
            self.editor_widget.clear_log()
            self.statusBar().showMessage(
                f"Đã tải: {display_name}  —  {len(self._cities)} thành phố"
                f"  —  {len(self._depots)} Depots"
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Tải Dữ liệu",
                                 f"Đã xảy ra lỗi khi đọc File: {str(e)}")

    # ------------------------------------------------------------------
    def _on_customize_depots(self):
        """Mở cửa sổ chọn Kho hàng."""
        if not self._cities:
            return
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QListWidget,
            QListWidgetItem, QDialogButtonBox, QLabel
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("📍 Chọn Kho Hàng (Depots)")
        dialog.setMinimumSize(350, 450)
        dialog.setStyleSheet(
            "QDialog { background-color: #1e1e2e; color: #cdd6f4; font-size: 14px; }"
            "QListWidget { background: #313244; color: #cdd6f4; font-size: 14px;"
            "  padding: 5px; border-radius: 5px; }"
        )

        layout = QVBoxLayout(dialog)
        lbl = QLabel("Tích chọn các thành phố sẽ đóng vai trò là Kho hàng (Depot):")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        list_widget = QListWidget()
        for city in self._cities:
            item = QListWidgetItem(city)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if city in self._depots
                else Qt.CheckState.Unchecked
            )
            list_widget.addItem(item)
        layout.addWidget(list_widget)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setStyleSheet(
            "QPushButton { background-color: #89b4fa; color: #1e1e2e;"
            "  font-weight: bold; padding: 5px 15px; border-radius: 4px; }"
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_depots = [
                list_widget.item(i).text()
                for i in range(list_widget.count())
                if list_widget.item(i).checkState() == Qt.CheckState.Checked
            ]
            if not new_depots:
                QMessageBox.warning(self, "Lỗi", "Bạn phải chọn ít nhất 1 Kho hàng!")
                return

            self._depots = new_depots
            for city in self._cities:
                if city in self._depots:
                    self._demands[city] = 0

            self.map_widget.show_map(self._coords, self._depots)
            self.editor_widget.update_plot(self._coords, self._depots)
            self.statusBar().showMessage(
                f"✅ Đã cập nhật thành công {len(self._depots)} Depots."
            )

    # ------------------------------------------------------------------
    def _on_point_added(self, lat: float, lon: float, is_depot: bool):
        """Xử lý khi người dùng click chuột lên sơ đồ để thêm điểm."""
        from ga_core.cost_matrix import haversine_matrix

        # Tạo tên mới duy nhất
        self._point_counter += 1
        prefix = "D" if is_depot else "C"
        new_name = f"{prefix}_{self._point_counter}"
        
        # Thêm vào dữ liệu
        self._cities.append(new_name)
        self._coords[new_name] = (lat, lon)
        if is_depot:
            self._depots.append(new_name)
        
        # Mặc định demand và phí
        if self._handling is not None: self._handling[new_name] = 10.0
        if self._demands is not None: self._demands[new_name] = 10 if not is_depot else 0
        if self._time_windows is not None: self._time_windows[new_name] = (480, 1440)
        if self._service_times is not None: self._service_times[new_name] = 30
        
        # QUAN TRỌNG: Tính toán lại Cost Matrix bằng Haversine (NumPy vectorized)
        self._cost_matrix, self._city_index = haversine_matrix(self._cities, self._coords)
        
        # Cập nhật hiển thị
        self.map_widget.show_map(self._coords, self._depots)
        self.editor_widget.update_plot(self._coords, self._depots)
        self.editor_widget.add_log_entry(new_name, lat, lon, is_depot) # THÊM VÀO LOG
        
        type_str = "Kho hàng" if is_depot else "Khách hàng"
        self.statusBar().showMessage(f"📍 Đã thêm {type_str}: {new_name} ({lat:.4f}, {lon:.4f})")

    def _on_point_removed(self, lat: float, lon: float):
        """Xóa điểm gần nhất với vị trí click chuột giữa."""
        if not self._cities:
            return

        from ga_core.cost_matrix import haversine_matrix
        # Tìm điểm gần nhất
        min_dist = float("inf")
        target_city = None
        
        for city, (p_lat, p_lon) in self._coords.items():
            # Sử dụng công thức đơn giản để tìm điểm gần nhất trên màn hình
            d = (p_lat - lat)**2 + (p_lon - lon)**2
            if d < min_dist:
                min_dist = d
                target_city = city

        # Kiểm tra nếu khoảng cách đủ gần (để tránh xóa nhầm khi click vào chỗ trống)
        if target_city:
            # Xóa khỏi dữ liệu
            self._cities.remove(target_city)
            del self._coords[target_city]
            if target_city in self._depots:
                self._depots.remove(target_city)
            if self._handling: del self._handling[target_city]
            if self._demands: del self._demands[target_city]
            if self._time_windows: del self._time_windows[target_city]
            if self._service_times: del self._service_times[target_city]

            # Tính lại ma trận
            self._cost_matrix, self._city_index = haversine_matrix(self._cities, self._coords)

            # Cập nhật hiển thị
            self.map_widget.show_map(self._coords, self._depots)
            self.editor_widget.update_plot(self._coords, self._depots)
            self.editor_widget.remove_log_entry(target_city) # XÓA KHỎI LOG
            self.statusBar().showMessage(f"🗑 Đã xóa điểm: {target_city}")

    def _on_undo(self):
        """Hoàn tác: xóa điểm cuối cùng được thêm."""
        if not self._cities:
            return
        last_city = self._cities[-1]
        # Ta có thể gọi luôn _on_point_removed với tọa độ của last_city
        lat, lon = self._coords[last_city]
        self._on_point_removed(lat, lon)

    def _on_clear_custom(self):
        """Xóa sạch các điểm tự vẽ (giữ lại dataset gốc nếu cần)."""
        if QMessageBox.question(self, "Xác nhận", "Xóa toàn bộ các điểm hiện tại?") == QMessageBox.StandardButton.Yes:
            self._cities = []
            self._coords = {}
            self._depots = []
            self._handling = {}
            self._demands = {}
            self._time_windows = {}
            self._service_times = {}
            self._cost_matrix = np.array([[]])
            self._city_index = {}
            self.editor_widget.clear_log()
            self.map_widget.show_map({}, [])
            self.editor_widget.update_plot({}, [])
            self.statusBar().showMessage("🧹 Đã xóa sạch bản đồ.")

    # ------------------------------------------------------------------
    def _on_run(self):
        """Bắt đầu chạy GA."""
        self._global_best_cost = float("inf")
        self._global_best_gen = 0
        self._global_best_fitness = 0.0
        self._global_best_conflicts = 0
        self._global_best_capacity_overload = 0.0
        self._global_best_capacity_overload_details = []
        self._last_map_update_time = time.time()
        self._last_status_update_time = time.time()

        params = self.control.get_params()
        self._run_params = dict(params)
        algorithm_choice = params.get("algorithm", "GA")
        traffic_event = params.get("traffic_event", 0)
        self._run_started_at = time.perf_counter()
        self._run_algorithm = algorithm_choice
        depot_set = set(self._depots or [])
        active_demands = dict(self._demands or {})

        if params.get("use_capacity", False):
            cargo_weight = params.get("cargo_weight_per_customer", 0)
            for city in self._cities:
                active_demands[city] = 0 if city in depot_set else cargo_weight
        self._active_demands = active_demands

        modified_cost_matrix: np.ndarray = self._cost_matrix.copy()
        self._active_cost_matrix = modified_cost_matrix
        self._blocked_edges = []

        if traffic_event == 1:
            n = modified_cost_matrix.shape[0]
            mask = np.random.random((n, n)) < 0.4
            factor = np.random.uniform(1.2, 2.0, (n, n))
            finite_mask = np.isfinite(modified_cost_matrix) & mask
            modified_cost_matrix[finite_mask] *= factor[finite_mask]
            self.statusBar().showMessage(
                "🌧️ Đang chạy (Mưa bão): Phí di chuyển bị tăng ngẫu nhiên!"
            )

        elif traffic_event == 2:
            cities_list = list(self._cities)
            num_blocks = max(1, int(len(cities_list) * 0.4))
            for _ in range(num_blocks):
                c1 = random.choice(cities_list)
                c2 = random.choice(cities_list)
                if c1 != c2:
                    i1 = self._city_index.get(c1)
                    i2 = self._city_index.get(c2)
                    if i1 is not None and i2 is not None:
                        modified_cost_matrix[i1, i2] = np.inf
                        modified_cost_matrix[i2, i1] = np.inf
                        self._blocked_edges.append((c1, c2))
            if self._blocked_edges:
                self.statusBar().showMessage(
                    f"💥 Đang chạy (Tai nạn): Đã phong toả {len(self._blocked_edges)} tuyến đường!"
                )

        core_kwargs = {
            "cities":           self._cities,
            "depots":           self._depots,
            "cost_matrix":      modified_cost_matrix,
            "city_index":       self._city_index,
            "handling_fees":    self._handling,
            "demands":          self._active_demands,
            "max_capacity":     params.get("max_capacity", 200),
            "coords":           self._coords,
            "pop_size":         params["pop_size"],
            "crossover_rate":   params["crossover_rate"],
            "mutation_rate":    params["mutation_rate"],
            "generations":      params["generations"],
            "tournament_size":  params["tournament_size"],
            "num_vehicles":     params["num_vehicles"],
            "elitism_count":    params["elitism_count"],
            "time_windows":     self._time_windows,
            "service_times":    self._service_times,
            "use_capacity":     params.get("use_capacity", False),
            "use_tw":           params.get("use_tw", False),
            "capacity_penalty_weight": params.get(
                "capacity_penalty_weight",
                DEFAULT_CAPACITY_PENALTY_WEIGHT,
            ),
        }

        self.control.set_running(True)
        self.chart_widget.reset()
        self._workers = []
        self._ab_finished_count = 0
        self._best_routes_overall = None
        self._global_best_cost = float("inf")
        self._global_best_fitness = 0.0
        self._global_best_conflicts = 0
        self._global_best_capacity_overload = 0.0
        self._global_best_capacity_overload_details = []
        self._ab_metrics = {}
        self._single_metrics = None

        if "A/B Testing" in algorithm_choice:
            self.chart_widget.set_mode("AB_TESTING")
            self._ab_metrics = {
                "GA": self._new_algo_metrics("GA"),
                "CSO": self._new_algo_metrics("CSO"),
            }

            engine_ga = GAEngine(**core_kwargs)
            worker_ga = GAWorker(engine_ga)
            worker_ga.generation_done.connect(
                lambda gen, fit, cost, conf, routes:
                    self._on_ab_generation("GA", gen, fit, cost, conf, routes)
            )
            worker_ga.finished_signal.connect(
                lambda routes: self._on_ab_finished("GA", routes)
            )

            engine_cso = CSOEngine(**core_kwargs)
            worker_cso = CSOWorker(engine_cso)
            worker_cso.generation_done.connect(
                lambda gen, fit, cost, conf, routes:
                    self._on_ab_generation("CSO", gen, fit, cost, conf, routes)
            )
            worker_cso.finished_signal.connect(
                lambda routes: self._on_ab_finished("CSO", routes)
            )

            self._workers.extend([worker_ga, worker_cso])
            self.statusBar().showMessage("🔄 Đang chạy A/B Testing: GA và CSO...")
            self._ab_metrics["GA"]["started_at"] = time.perf_counter()
            worker_ga.start()
            self._ab_metrics["CSO"]["started_at"] = time.perf_counter()
            worker_cso.start()

        elif "CSO" in algorithm_choice:
            self.chart_widget.set_mode("SINGLE")
            engine = CSOEngine(**core_kwargs)
            self._single_metrics = self._new_algo_metrics("CSO")
            self._single_metrics["started_at"] = time.perf_counter()
            worker = CSOWorker(engine)
            worker.generation_done.connect(self._on_generation)
            worker.finished_signal.connect(self._on_finished)
            self._workers.append(worker)
            self.statusBar().showMessage("🔄 Đang chạy thuật toán: CSO...")
            worker.start()

        else:
            self.chart_widget.set_mode("SINGLE")
            engine = GAEngine(**core_kwargs)
            self._single_metrics = self._new_algo_metrics("GA")
            self._single_metrics["started_at"] = time.perf_counter()
            worker = GAWorker(engine)
            worker.generation_done.connect(self._on_generation)
            worker.finished_signal.connect(self._on_finished)
            self._workers.append(worker)
            self.statusBar().showMessage("🔄 Đang chạy thuật toán: GA...")
            worker.start()

    # ------------------------------------------------------------------
    def _on_stop(self):
        for w in self._workers:
            w.stop()
        self.control.set_running(False)
        self.statusBar().showMessage("⏹ Đã dừng thuật toán.")

    # ------------------------------------------------------------------
    def _on_reset(self):
        self._on_stop()
        self.chart_widget.reset()
        self.control.update_results(0, 0.0, 0.0, 0)
        self.map_widget.show_map(self._coords, self._depots)
        self.editor_widget.update_plot(self._coords, self._depots)
        self.statusBar().showMessage("🗑 Đã reset.")

    # ------------------------------------------------------------------
    @staticmethod
    def _new_algo_metrics(algo: str) -> dict:
        return {
            "algo": algo,
            "started_at": None,
            "elapsed": None,
            "best_cost": float("inf"),
            "best_fitness": 0.0,
            "best_conflicts": 0,
            "best_capacity_overload": 0.0,
            "best_capacity_overload_details": [],
            "best_gen": 0,
            "updates": 0,
            "routes": None,
        }

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        if seconds is None:
            return "N/A"
        return f"{seconds:.3f}s"

    @staticmethod
    def _quality_gap(candidate: float, best: float) -> float:
        if best <= 0 or not np.isfinite(candidate) or not np.isfinite(best):
            return 0.0
        return ((candidate - best) / best) * 100.0

    def _capacity_overload_details(
        self,
        routes: list,
        max_capacity: int,
    ):
        depot_set = set(self._depots or [])
        demands = getattr(self, "_active_demands", self._demands) or {}
        details = []

        for index, route in enumerate(routes or [], start=1):
            load = 0
            visited = set()
            for city in route:
                if city in visited:
                    continue
                visited.add(city)
                if city not in depot_set:
                    load += demands.get(city, 0)

            overflow = max(0, load - max_capacity)
            if overflow > 0:
                details.append({
                    "vehicle": index,
                    "load": load,
                    "overflow": overflow,
                })

        total_overload = sum(item["overflow"] for item in details)
        return total_overload, details

    @staticmethod
    def _format_capacity_overload(total_overload: float, details: list, use_capacity: bool) -> str:
        if not use_capacity:
            return ""
        if total_overload <= 0:
            return "  —  Quá tải: 0 kg"

        preview = ", ".join(
            f"Xe {item['vehicle']} +{item['overflow']:,.0f} kg"
            for item in details[:3]
        )
        if len(details) > 3:
            preview += ", ..."
        return f"  —  Quá tải: +{total_overload:,.0f} kg ({preview})"

    # ------------------------------------------------------------------
    def _on_generation(self, gen: int, fitness: float, cost: float, conflicts: int, routes: list):
        """Callback mỗi thế hệ."""
        now = time.time()
        params = getattr(self, "_run_params", None) or self.control.get_params()
        improved = False
        if self._single_metrics is not None:
            self._single_metrics["updates"] += 1
        if cost < self._global_best_cost - 1e-5:
            overload, overload_details = self._capacity_overload_details(
                routes,
                params.get("max_capacity", 200),
            )
            self._global_best_cost = cost
            self._global_best_gen = gen
            self._global_best_fitness = fitness
            self._global_best_conflicts = conflicts
            self._global_best_capacity_overload = overload
            self._global_best_capacity_overload_details = overload_details
            if self._single_metrics is not None:
                self._single_metrics.update({
                    "best_cost": cost,
                    "best_fitness": fitness,
                    "best_conflicts": conflicts,
                    "best_capacity_overload": overload,
                    "best_gen": gen,
                    "routes": routes,
                })
            improved = True

        self.chart_widget.update_chart(gen, cost)

        if now - self._last_status_update_time >= 0.2 or gen == self.control.sp_gen.value():
            self.control.update_results(
                self._global_best_gen,
                self._global_best_cost,
                self._global_best_fitness,
                self._global_best_conflicts,
                self._global_best_capacity_overload
                if params.get("use_capacity", False) else 0.0,
            )
            overload_status = self._format_capacity_overload(
                self._global_best_capacity_overload,
                self._global_best_capacity_overload_details,
                params.get("use_capacity", False),
            )
            self.statusBar().showMessage(
                f"Thế hệ {gen}  —  Best objective: {self._global_best_cost:,.1f}"
                f" (Xung đột: {self._global_best_conflicts})"
                f"{overload_status}"
                f"  —  Fitness: {self._global_best_fitness:.6e}"
            )
            self._last_status_update_time = now

        significant = (cost < self._global_best_cost * 0.999)
        time_to_update = (now - self._last_map_update_time >= 1.5)

        if (improved and (significant or time_to_update)) or gen == 1 or gen == self.control.sp_gen.value():
            self.map_widget.show_map(
                self._coords, self._depots, routes,
                gen, self._global_best_cost, self._global_best_gen,
                is_final=(gen == self.control.sp_gen.value())
            )
            self._last_map_update_time = now

    # ------------------------------------------------------------------
    def _on_ab_generation(self, algo: str, gen: int, fitness: float, cost: float, conflicts: int, routes: list):
        now = time.time()
        params = getattr(self, "_run_params", None) or self.control.get_params()
        improved = False
        metrics = self._ab_metrics.get(algo)
        if metrics is not None:
            metrics["updates"] += 1
            if cost < metrics["best_cost"] - 1e-5:
                overload, overload_details = self._capacity_overload_details(
                    routes,
                    params.get("max_capacity", 200),
                )
                metrics.update({
                    "best_cost": cost,
                    "best_fitness": fitness,
                    "best_conflicts": conflicts,
                    "best_capacity_overload": overload,
                    "best_capacity_overload_details": overload_details,
                    "best_gen": gen,
                    "routes": routes,
                })
        if cost < self._global_best_cost - 1e-5:
            overload, overload_details = self._capacity_overload_details(
                routes,
                params.get("max_capacity", 200),
            )
            self._global_best_cost = cost
            self._global_best_gen = gen
            self._global_best_fitness = fitness
            self._global_best_conflicts = conflicts
            self._global_best_capacity_overload = overload
            self._global_best_capacity_overload_details = overload_details
            self._best_routes_overall = routes
            improved = True
 
        self.chart_widget.update_chart_ab(algo, gen, cost)
 
        if now - getattr(self, "_last_status_update_time", 0) >= 0.2:
            self.control.update_results(
                self._global_best_gen,
                self._global_best_cost,
                self._global_best_fitness,
                self._global_best_conflicts,
                self._global_best_capacity_overload
                if params.get("use_capacity", False) else 0.0,
            )
            overload_status = self._format_capacity_overload(
                self._global_best_capacity_overload,
                self._global_best_capacity_overload_details,
                params.get("use_capacity", False),
            )
            self.statusBar().showMessage(
                f"A/B Testing  —  Best objective: {self._global_best_cost:,.1f}"
                f" (Gen {self._global_best_gen} / {algo})"
                f"  —  Xung đột: {self._global_best_conflicts}"
                f"{overload_status}"
            )
            self._last_status_update_time = now

        significant = (cost < self._global_best_cost * 0.999)
        time_to_update = (now - getattr(self, "_last_map_update_time", 0) >= 2.0)

        if improved and (significant or time_to_update):
            self.map_widget.show_map(
                self._coords, self._depots, routes,
                gen, self._global_best_cost, self._global_best_gen,
                getattr(self, "_blocked_edges", None),
                is_final=False # Luôn dùng PolyLine cho A/B Testing để mượt
            )
            self._last_map_update_time = now

    def _on_ab_finished(self, algo: str, routes: list):
        metrics = self._ab_metrics.get(algo)
        if metrics is not None:
            started_at = metrics.get("started_at")
            metrics["elapsed"] = (
                time.perf_counter() - started_at if started_at is not None else None
            )
            if metrics.get("routes") is None:
                metrics["routes"] = routes
        self._ab_finished_count += 1
        if self._ab_finished_count >= len(self._workers):
            self._on_finished(self._best_routes_overall or routes)
            self._show_ab_comparison()

    def _show_ab_comparison(self):
        ga = self._ab_metrics.get("GA")
        cso = self._ab_metrics.get("CSO")
        if not ga or not cso:
            return

        best_value = min(ga["best_cost"], cso["best_cost"])
        winner_quality = "GA" if ga["best_cost"] <= cso["best_cost"] else "CSO"
        winner_time = "GA" if (ga["elapsed"] or float("inf")) <= (cso["elapsed"] or float("inf")) else "CSO"
        ga_gap = self._quality_gap(ga["best_cost"], best_value)
        cso_gap = self._quality_gap(cso["best_cost"], best_value)

        message = (
            "So sánh GA / CSO\n\n"
            f"GA:  Objective={ga['best_cost']:,.1f}, Gen tốt nhất={ga['best_gen']}, "
            f"Vi phạm={ga['best_conflicts']}, Time={self._format_elapsed(ga['elapsed'])}, "
            f"Gap={ga_gap:.2f}%\n"
            f"CSO: Objective={cso['best_cost']:,.1f}, Gen tốt nhất={cso['best_gen']}, "
            f"Vi phạm={cso['best_conflicts']}, Time={self._format_elapsed(cso['elapsed'])}, "
            f"Gap={cso_gap:.2f}%\n\n"
            f"Tốt hơn theo chất lượng nghiệm: {winner_quality}\n"
            f"Nhanh hơn theo thời gian chạy: {winner_time}"
        )
        self.statusBar().showMessage(
            f"A/B xong: quality={winner_quality}, time={winner_time}, "
            f"GA {self._format_elapsed(ga['elapsed'])}, CSO {self._format_elapsed(cso['elapsed'])}"
        )
        self.chart_widget.update_ab_stats(ga, cso)

    # ------------------------------------------------------------------
    def _on_export_map(self):
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu Bản đồ", "vrp_map.png",
            "PNG Files (*.png);;JPEG Files (*.jpg)"
        )
        if file_path:
            self.map_widget.grab().save(file_path)
            self.statusBar().showMessage(f"📸 Đã lưu bản đồ tại: {file_path}")

    # ------------------------------------------------------------------
    def _on_finished(self, best_routes: list):
        """GA/CSO hoàn thành."""
        self.control.set_running(False)
        params = getattr(self, "_run_params", None) or self.control.get_params()

        if hasattr(self.chart_widget, "_do_draw"):
            self.chart_widget._do_draw()

        cost = getattr(self, "_global_best_cost", 0.0)
        best_gen = getattr(self, "_global_best_gen", self.control.sp_gen.value())
        elapsed = None
        if self._single_metrics is not None:
            started_at = self._single_metrics.get("started_at")
            elapsed = time.perf_counter() - started_at if started_at is not None else None
            self._single_metrics["elapsed"] = elapsed
            self.chart_widget.update_single_stats(
                self._single_metrics["algo"],
                cost,
                best_gen,
                getattr(self, "_global_best_conflicts", 0),
                elapsed,
            )
        elapsed_status = f"  —  Time: {self._format_elapsed(elapsed)}" if elapsed is not None else ""
        elapsed_message = f"• Thời gian chạy: {self._format_elapsed(elapsed)}\n" if elapsed is not None else ""

        self.map_widget.show_map(
            self._coords, self._depots, best_routes,
            generation=self.control.sp_gen.value(),
            best_cost=cost,
            best_gen=best_gen,
            blocked_edges=getattr(self, "_blocked_edges", None),
            is_final=True, # Bản cuối bật hiệu ứng đẹp
        )

        # CẬP NHẬT: Đảm bảo bảng Control Panel hiển thị đúng kết quả tốt nhất cuối cùng
        self.control.update_results(
            best_gen,
            cost,
            getattr(self, "_global_best_fitness", 0.0),
            getattr(self, "_global_best_conflicts", 0),
            getattr(self, "_global_best_capacity_overload", 0.0)
            if params.get("use_capacity", False) else 0.0,
        )
        self.editor_widget.update_plot(self._coords, self._depots, best_routes)

        # THAY ĐỔI: tính route_costs dùng numpy lookup thay vì dict.get()
        depot_set = set(self._depots)
        num_stops = sum(len(r) - 2 for r in best_routes)
        route_costs = []
        route_loads = []

        for route in best_routes:
            r_cost = 0.0
            r_load = 0
            visited = set()

            for i in range(len(route) - 1):
                c1, c2 = route[i], route[i + 1]
                i1 = self._city_index.get(c1)
                i2 = self._city_index.get(c2)
                if i1 is not None and i2 is not None:
                    d = getattr(self, "_active_cost_matrix", self._cost_matrix)[i1, i2]
                    r_cost += 0.0 if np.isinf(d) else d

            for city in route:
                if city not in visited:
                    r_cost += self._handling.get(city, 0.0)
                    visited.add(city)
                    if city not in depot_set:
                        r_load += getattr(self, "_active_demands", self._demands).get(city, 0)

            route_costs.append(r_cost)
            route_loads.append(r_load)

        max_capacity = params.get("max_capacity", 200)
        capacity_penalty_weight = params.get(
            "capacity_penalty_weight",
            DEFAULT_CAPACITY_PENALTY_WEIGHT,
        )
        cargo_weight = params.get("cargo_weight_per_customer", 0)
        capacity_overload_details = []
        total_capacity_overload = 0
        if params.get("use_capacity", False):
            for index, load in enumerate(route_loads, start=1):
                overflow = max(0, load - max_capacity)
                if overflow > 0:
                    capacity_overload_details.append({
                        "vehicle": index,
                        "load": load,
                        "overflow": overflow,
                    })
                    total_capacity_overload += overflow
        capacity_penalty = total_capacity_overload * capacity_penalty_weight
        self.control.update_results(
            best_gen,
            cost,
            getattr(self, "_global_best_fitness", 0.0),
            getattr(self, "_global_best_conflicts", 0),
            total_capacity_overload,
        )

        self.dashboard_widget.update_dashboard(
            cost=cost,
            num_vehicles=len(best_routes),
            gen=best_gen,
            num_stops=num_stops,
            routes=best_routes,
            route_costs=route_costs,
            route_loads=route_loads,
            max_capacity=max_capacity,
            time_windows=self._time_windows,
            service_times=self._service_times,
            use_tw=params.get("use_tw", False),
            use_capacity=params.get("use_capacity", False),
        )

        capacity_status = self._format_capacity_overload(
            total_capacity_overload,
            capacity_overload_details,
            params.get("use_capacity", False),
        )

        capacity_message = ""
        if params.get("use_capacity", False):
            if total_capacity_overload > 0:
                detail_text = ", ".join(
                    f"Xe {item['vehicle']} vượt {item['overflow']:,.0f} kg"
                    for item in capacity_overload_details
                )
                capacity_message = (
                    f"• Kg hàng/khách: {cargo_weight:,.0f} kg\n"
                    f"• Vượt tải CVRP: +{total_capacity_overload:,.0f} kg\n"
                    f"• Hệ số vượt tải: {capacity_penalty_weight:,.0f}\n"
                    f"• Penalty tải trọng: {capacity_penalty:,.1f}\n"
                    f"• Tuyến vượt tải: {detail_text}\n"
                )
            else:
                capacity_message = (
                    f"• Kg hàng/khách: {cargo_weight:,.0f} kg\n"
                    f"• Hệ số vượt tải: {capacity_penalty_weight:,.0f}\n"
                    "• Vượt tải CVRP: 0 kg\n"
                )

        self.statusBar().showMessage(
            f"✅ Hoàn thành!  Objective: {cost:,.1f} (Tại Gen {best_gen})"
            f"  —  {len(best_routes)} tuyến xe"
            f"{capacity_status}"
            f"{elapsed_status}"
        )

        QMessageBox.information(
            self, "Trí tuệ nhân tạo Hoàn thành",
            f"Hệ thống đã phân tuyến xong!\n\n"
            f"• Lời giải tốt nhất tại thế hệ: {best_gen}\n"
            f"• Objective tốt nhất: {cost:,.1f}\n"
            f"{elapsed_message}"
            f"• Số tuyến xe: {len(best_routes)}\n"
            f"{capacity_message}"
            f"• Tổng khu vực: {len(self._cities)}",
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _global_style():
        return """
            QMainWindow, QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QLabel { color: #cdd6f4; }
            QSplitter::handle { background: #45475a; height: 3px; }
            QStatusBar {
                background: #181825;
                border-top: 1px solid #313244;
            }
        """
