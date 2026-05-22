"""
Control Panel — Panel điều khiển tham số GA & nút hành động.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QPushButton, QGroupBox, QFrame, QFileDialog, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from utils.constants import (
    DEFAULT_POPULATION_SIZE, DEFAULT_CROSSOVER_RATE,
    DEFAULT_MUTATION_RATE, DEFAULT_GENERATIONS,
    DEFAULT_TOURNAMENT_SIZE, DEFAULT_NUM_VEHICLES,
    DEFAULT_ELITISM_COUNT,
    DATASET_EUROPE, DATASET_VIETNAM, DATASET_HCMC,
)


class ControlPanel(QWidget):
    """Panel bên trái — nhập tham số GA & chọn dataset."""

    # Signals
    run_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    dataset_changed = pyqtSignal(str)
    customize_depots_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(310)
        self._build_ui()

    # -----------------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── Title ──
        title = QLabel("🧬 VRP — Giải thuật Di truyền")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: #cdd6f4;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # ── Dataset ──
        ds_group = self._group("📂 Bộ dữ liệu")
        ds_layout = QVBoxLayout(ds_group)
        self.cmb_dataset = QComboBox()
        self.cmb_dataset.addItems([DATASET_EUROPE, DATASET_VIETNAM, DATASET_HCMC, "Import Custom (CSV)..."])
        self.cmb_dataset.currentTextChanged.connect(self._on_dataset_combo_changed)
        self.cmb_dataset.setStyleSheet(self._combo_style())
        ds_layout.addWidget(self.cmb_dataset)
        
        self.btn_customize_depots = QPushButton("📍 Tùy chỉnh Kho hàng")
        self.btn_customize_depots.setStyleSheet(self._btn_style("#89dceb", "#1e1e2e"))
        self.btn_customize_depots.clicked.connect(self.customize_depots_clicked.emit)
        ds_layout.addWidget(self.btn_customize_depots)
        
        main_layout.addWidget(ds_group)
        
        # ── Ngoại cảnh ──
        env_group = self._group("🌪️ Biến cố Ngoại cảnh")
        env_layout = QVBoxLayout(env_group)
        self.cmb_traffic = QComboBox()
        self.cmb_traffic.addItems([
            "☀️ Bình thường",
            "🌧️ Mưa bão (Phí di chuyển x1.5)",
            "💥 Tai nạn / Kẹt xe (Chặn đường)"
        ])
        self.cmb_traffic.setStyleSheet(self._combo_style())
        env_layout.addWidget(self.cmb_traffic)
        main_layout.addWidget(env_group)

        # ── Tham số Thuật toán ──
        algo_group = self._group("⚙️ Tham số Thuật toán")
        self.form_algo = QFormLayout(algo_group)
        self.form_algo.setVerticalSpacing(6)

        self.cmb_algorithm = QComboBox()
        self.cmb_algorithm.addItems(["Trí tuệ Nhân tạo di truyền (GA)", "Tối ưu hoá Bầy Mèo (CSO)", "So sánh GA và CSO (A/B Testing)"])
        self.cmb_algorithm.setStyleSheet(self._combo_style())
        self.cmb_algorithm.currentTextChanged.connect(self._on_algo_changed)
        self.form_algo.addRow("Loại Thuật toán:", self.cmb_algorithm)

        self.sp_pop = self._spin(10, 2000, DEFAULT_POPULATION_SIZE)
        self.form_algo.addRow("Quần thể (n):", self.sp_pop)

        self.sp_gen = self._spin(10, 5000, DEFAULT_GENERATIONS)
        self.form_algo.addRow("Số thế hệ:", self.sp_gen)

        self.sp_cx = self._dspin(0.0, 1.0, DEFAULT_CROSSOVER_RATE, 0.05)
        self.form_algo.addRow("Lai ghép / MR:", self.sp_cx)

        self.sp_mu = self._dspin(0.0, 1.0, DEFAULT_MUTATION_RATE, 0.01)
        self.form_algo.addRow("Đột biến / SR:", self.sp_mu)

        self.sp_tour = self._spin(2, 20, DEFAULT_TOURNAMENT_SIZE)
        self.form_algo.addRow("K-Select / SMP:", self.sp_tour)

        self.sp_vehicles = self._spin(1, 10, DEFAULT_NUM_VEHICLES)
        self.form_algo.addRow("Số xe:", self.sp_vehicles)

        self.sp_capacity = self._spin(10, 2000, 200)
        self.form_algo.addRow("Tải trọng xe:", self.sp_capacity)

        self.sp_cargo_weight = self._spin(1, 2000, 30)
        self.form_algo.addRow("Kg hàng/khách:", self.sp_cargo_weight)

        self.sp_capacity_penalty = self._spin(1_000, 1_000_000, 10_000)
        self.form_algo.addRow("Hệ số vượt tải:", self.sp_capacity_penalty)

        self.sp_elite = self._spin(0, 20, DEFAULT_ELITISM_COUNT)
        self.form_algo.addRow("Elitism:", self.sp_elite)

        self.chk_capacity = self._check("Bật ràng buộc Tải trọng (CVRP)")
        self.form_algo.addRow("", self.chk_capacity)

        self.chk_tw = self._check("Bật ràng buộc Thời gian (TW)")
        self.form_algo.addRow("", self.chk_tw)

        main_layout.addWidget(algo_group)
        self._on_algo_changed(self.cmb_algorithm.currentText())

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("▶  Chạy")
        self.btn_run.setStyleSheet(self._btn_style("#a6e3a1", "#1e1e2e"))
        self.btn_run.setMinimumHeight(36)
        self.btn_run.clicked.connect(self.run_clicked.emit)

        self.btn_stop = QPushButton("⏹  Dừng")
        self.btn_stop.setStyleSheet(self._btn_style("#f38ba8", "#1e1e2e"))
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)

        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_stop)
        main_layout.addLayout(btn_layout)

        self.btn_reset = QPushButton("🗑  Reset")
        self.btn_reset.setStyleSheet(self._btn_style("#cba6f7", "#1e1e2e"))
        self.btn_reset.setMinimumHeight(32)
        self.btn_reset.clicked.connect(self.reset_clicked.emit)
        main_layout.addWidget(self.btn_reset)

        # ── Results ──
        res_group = self._group("📊 Kết quả")
        res_layout = QFormLayout(res_group)
        self.lbl_gen = QLabel("—")
        self.lbl_cost = QLabel("—")
        self.lbl_fitness = QLabel("—")
        self.lbl_conflicts = QLabel("—") # THÊM MỚI
        for lbl in (self.lbl_gen, self.lbl_cost, self.lbl_fitness, self.lbl_conflicts):
            lbl.setStyleSheet("color:#89b4fa; font-weight:bold; font-size:12px;")
        res_layout.addRow("Thế hệ:", self.lbl_gen)
        res_layout.addRow("Objective:", self.lbl_cost)
        res_layout.addRow("Fitness:", self.lbl_fitness)
        res_layout.addRow("⚠️ Số vi phạm:", self.lbl_conflicts) # HIỂN THỊ VI PHẠM
        main_layout.addWidget(res_group)

        main_layout.addStretch()

    # -----------------------------------------------------------------
    # Logic Handle Combo
    # -----------------------------------------------------------------
    def _on_dataset_combo_changed(self, text):
        if text == "Import Custom (CSV)...":
            file_path, _ = QFileDialog.getOpenFileName(self, "Tải Định dạng CSV", "", "CSV Files (*.csv)")
            if file_path:
                self.dataset_changed.emit(file_path)
            else:
                self.cmb_dataset.blockSignals(True)
                self.cmb_dataset.setCurrentIndex(0)
                self.cmb_dataset.blockSignals(False)
        else:
            self.dataset_changed.emit(text)

    # -----------------------------------------------------------------
    def _on_algo_changed(self, text):
        if "CSO" in text:
            self.form_algo.labelForField(self.sp_cx).setText("Mixture Ratio (MR):")
            self.form_algo.labelForField(self.sp_mu).setText("Seeking Range (SR):")
            self.form_algo.labelForField(self.sp_tour).setText("Memory Pool (SMP):")
        else:
            self.form_algo.labelForField(self.sp_cx).setText("Crossover (r_co):")
            self.form_algo.labelForField(self.sp_mu).setText("Mutation (r_mu):")
            self.form_algo.labelForField(self.sp_tour).setText("Tournament k:")

    # -----------------------------------------------------------------
    # Getters
    # -----------------------------------------------------------------
    def get_params(self) -> dict:
        return {
            "algorithm": self.cmb_algorithm.currentText(),
            "dataset": self.cmb_dataset.currentText(),
            "pop_size": self.sp_pop.value(),
            "generations": self.sp_gen.value(),
            "crossover_rate": self.sp_cx.value(),
            "mutation_rate": self.sp_mu.value(),
            "tournament_size": self.sp_tour.value(),
            "num_vehicles": self.sp_vehicles.value(),
            "max_capacity": self.sp_capacity.value(),
            "cargo_weight_per_customer": self.sp_cargo_weight.value(),
            "capacity_penalty_weight": self.sp_capacity_penalty.value(),
            "elitism_count": self.sp_elite.value(),
            "use_capacity": self.chk_capacity.isChecked(),
            "use_tw": self.chk_tw.isChecked(),
            "traffic_event": self.cmb_traffic.currentIndex(),
        }

    def update_results(
        self,
        gen: int,
        cost: float,
        fitness: float,
        conflicts: int = 0,
        capacity_overload: float = 0.0,
    ):
        self.lbl_gen.setText(str(gen))
        self.lbl_cost.setText(f"{cost:,.1f}")
        self.lbl_fitness.setText(f"{fitness:.6e}")
        if capacity_overload > 0:
            self.lbl_conflicts.setText(f"{conflicts} (+{capacity_overload:,.0f} kg)")
        else:
            self.lbl_conflicts.setText(str(conflicts))
        if conflicts > 0:
            self.lbl_conflicts.setStyleSheet("color: #f38ba8; font-weight: bold;")
        else:
            self.lbl_conflicts.setStyleSheet("color: #a6e3a1; font-weight: bold;")

    def set_running(self, running: bool):
        self.btn_run.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    # -----------------------------------------------------------------
    # UI helpers
    # -----------------------------------------------------------------
    def _group(self, title: str) -> QGroupBox:
        g = QGroupBox(title)
        g.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 18px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)
        return g

    def _spin(self, lo, hi, val):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setStyleSheet(self._input_style())
        return s

    def _dspin(self, lo, hi, val, step):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setSingleStep(step)
        s.setDecimals(2)
        s.setStyleSheet(self._input_style())
        return s

    def _check(self, text):
        c = QCheckBox(text)
        c.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        return c

    @staticmethod
    def _input_style():
        return """
            QSpinBox, QDoubleSpinBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 3px 6px;
            }
        """

    @staticmethod
    def _combo_style():
        return """
            QComboBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView {
                background: #313244;
                color: #cdd6f4;
                selection-background-color: #585b70;
            }
        """

    @staticmethod
    def _btn_style(bg: str, fg: str):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
            QPushButton:disabled {{
                background-color: #45475a;
                color: #6c7086;
            }}
        """
