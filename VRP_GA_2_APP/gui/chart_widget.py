"""
Chart Widget — Biểu đồ Fitness / Cost convergence qua các thế hệ.
Sử dụng Matplotlib nhúng trong PyQt6 (FigureCanvasQTAgg).
"""

import matplotlib
matplotlib.use("QtAgg")                # backend Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QWidget, QVBoxLayout


class ChartWidget(QWidget):
    """Biểu đồ convergence: Chi phí tốt nhất theo thế hệ."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Tạo Figure & Canvas
        self.figure = Figure(figsize=(5, 2.2), dpi=100)
        self.figure.patch.set_facecolor("#1e1e2e")
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.canvas, stretch=3)
        self._build_stats_panel(layout)

        # Dữ liệu
        self._mode = "SINGLE"
        self._generations = []
        self._costs = []
        self._ab_data = {"GA": ([], []), "CSO": ([], [])}

        self._init_axes()

    # -----------------------------------------------------------------
    def _build_stats_panel(self, parent_layout):
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            "QFrame { background:#181825; border:1px solid #313244; border-radius:8px; }"
            "QLabel { color:#cdd6f4; }"
        )
        grid = QGridLayout(self.stats_frame)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)

        self.lbl_stats_title = QLabel("Thống kê hội tụ")
        self.lbl_stats_title.setStyleSheet("font-size:14px; font-weight:bold; color:#a6e3a1;")
        grid.addWidget(self.lbl_stats_title, 0, 0, 1, 4)

        self._stat_labels = {}
        for i, key in enumerate(("best", "gen", "time", "gap", "conflicts", "winner")):
            title = {
                "best": "Best objective",
                "gen": "Gen tốt nhất",
                "time": "Thời gian",
                "gap": "Gap",
                "conflicts": "Vi phạm",
                "winner": "Kết luận",
            }[key]
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("font-size:11px; color:#a6adc8;")
            value_lbl = QLabel("—")
            value_lbl.setStyleSheet("font-size:13px; font-weight:bold; color:#89b4fa;")
            row = 1 + i // 3 * 2
            col = i % 3
            grid.addWidget(title_lbl, row, col)
            grid.addWidget(value_lbl, row + 1, col)
            self._stat_labels[key] = value_lbl

        self.lbl_stats_note = QLabel("Chạy thuật toán để cập nhật thống kê.")
        self.lbl_stats_note.setWordWrap(True)
        self.lbl_stats_note.setStyleSheet("font-size:12px; color:#a6adc8;")
        grid.addWidget(self.lbl_stats_note, 5, 0, 1, 3)

        parent_layout.addWidget(self.stats_frame, stretch=1)

    def reset_stats(self):
        self.lbl_stats_title.setText("Thống kê hội tụ")
        for label in self._stat_labels.values():
            label.setText("—")
        self.lbl_stats_note.setText("Chạy thuật toán để cập nhật thống kê.")

    def update_single_stats(
        self,
        algo: str,
        best_cost: float,
        best_gen: int,
        conflicts: int,
        elapsed: float = None,
    ):
        self.lbl_stats_title.setText(f"Thống kê {algo}")
        self._stat_labels["best"].setText(f"{best_cost:,.1f}")
        self._stat_labels["gen"].setText(str(best_gen))
        self._stat_labels["time"].setText("N/A" if elapsed is None else f"{elapsed:.3f}s")
        self._stat_labels["gap"].setText("0.00%")
        self._stat_labels["conflicts"].setText(str(conflicts))
        self._stat_labels["winner"].setText(algo)
        self.lbl_stats_note.setText(
            "Objective càng thấp càng tốt; thời gian được đo từ lúc bắt đầu chạy đến khi thuật toán hoàn tất."
        )

    def update_ab_stats(self, ga: dict, cso: dict):
        def fmt_time(value):
            return "N/A" if value is None else f"{value:.3f}s"

        best_value = min(ga["best_cost"], cso["best_cost"])
        winner_quality = "GA" if ga["best_cost"] <= cso["best_cost"] else "CSO"
        winner_time = "GA" if (ga["elapsed"] or float("inf")) <= (cso["elapsed"] or float("inf")) else "CSO"
        ga_gap = ((ga["best_cost"] - best_value) / best_value * 100.0) if best_value > 0 else 0.0
        cso_gap = ((cso["best_cost"] - best_value) / best_value * 100.0) if best_value > 0 else 0.0

        self.lbl_stats_title.setText("So sánh GA / CSO")
        self._stat_labels["best"].setText(
            f"GA {ga['best_cost']:,.1f} | CSO {cso['best_cost']:,.1f}"
        )
        self._stat_labels["gen"].setText(
            f"GA {ga['best_gen']} | CSO {cso['best_gen']}"
        )
        self._stat_labels["time"].setText(
            f"GA {fmt_time(ga['elapsed'])} | CSO {fmt_time(cso['elapsed'])}"
        )
        self._stat_labels["gap"].setText(
            f"GA {ga_gap:.2f}% | CSO {cso_gap:.2f}%"
        )
        self._stat_labels["conflicts"].setText(
            f"GA {ga['best_conflicts']} | CSO {cso['best_conflicts']}"
        )
        self._stat_labels["winner"].setText(
            f"Quality: {winner_quality} | Time: {winner_time}"
        )
        self.lbl_stats_note.setText(
            "Gap là phần trăm lệch so với nghiệm tốt nhất trong hai thuật toán. "
            "Quality dựa trên objective thấp hơn; Time dựa trên thời gian chạy ngắn hơn."
        )

    # -----------------------------------------------------------------
    def _init_axes(self):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor("#1e1e2e")
        self.ax.set_xlabel("Thế hệ", fontsize=9, color="#cdd6f4")
        self.ax.set_ylabel("Best objective", fontsize=9, color="#cdd6f4")
        self.ax.set_title("Convergence", fontsize=10, color="#cdd6f4", pad=8)
        self.ax.tick_params(colors="#a6adc8", labelsize=8)
        self.ax.spines["bottom"].set_color("#45475a")
        self.ax.spines["left"].set_color("#45475a")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.grid(True, alpha=0.15, color="#585b70")
        self.figure.tight_layout()

    # -----------------------------------------------------------------
    def set_mode(self, mode: str):
        self._mode = mode
        self.reset()

    def reset(self):
        """Xoá dữ liệu biểu đồ."""
        self._generations.clear()
        self._costs.clear()
        self._ab_data = {"GA": ([], []), "CSO": ([], [])}
        self.reset_stats()
        self._init_axes()
        self.canvas.draw()
        import time
        self._last_draw_time = time.time()

    # -----------------------------------------------------------------
    def update_chart_ab(self, algo: str, generation: int, best_cost: float):
        if algo in self._ab_data:
            gens, costs = self._ab_data[algo]
            gens.append(generation)
            costs.append(best_cost)
        self._throttle_draw()

    def update_chart(self, generation: int, best_cost: float):
        """Thêm điểm dữ liệu mới và vẽ lại (có giới hạn FPS)."""
        self._generations.append(generation)
        self._costs.append(best_cost)
        self._throttle_draw()

    def _throttle_draw(self):
        import time
        if not hasattr(self, '_last_draw_time'):
            self._last_draw_time = time.time()
            
        now = time.time()
        if now - self._last_draw_time >= 0.2:
            self._do_draw()
            self._last_draw_time = now

    def _do_draw(self):
        self.ax.clear()
        self.ax.set_facecolor("#1e1e2e")
        self.ax.set_xlabel("Thế hệ", fontsize=9, color="#cdd6f4")
        self.ax.set_ylabel("Best objective", fontsize=9, color="#cdd6f4")
        self.ax.set_title("Convergence", fontsize=10, color="#cdd6f4", pad=8)
        self.ax.tick_params(colors="#a6adc8", labelsize=8)
        self.ax.spines["bottom"].set_color("#45475a")
        self.ax.spines["left"].set_color("#45475a")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.grid(True, alpha=0.15, color="#585b70")

        if self._mode == "SINGLE":
            if not self._generations:
                self.canvas.draw()
                return

            self.ax.plot(self._generations, self._costs, color="#89b4fa", linewidth=1.5)

            min_c = min(self._costs)
            max_c = max(self._costs)
            diff = max_c - min_c if max_c > min_c else max_c * 0.1 if max_c > 0 else 1.0
            y_min = max(0, min_c - diff * 0.1)
            y_max = max_c + diff * 0.1
            self.ax.set_ylim(y_min, y_max)

            self.ax.fill_between(self._generations, self._costs, y_min, alpha=0.1, color="#89b4fa")

            min_idx = self._costs.index(min_c)
            best_gen = self._generations[min_idx]

            self.ax.plot(best_gen, min_c, "o", color="#a6e3a1", markersize=6, zorder=5)
            self.ax.annotate(f"{min_c:,.0f}\n(Gen {best_gen})", (best_gen, min_c), textcoords="offset points", xytext=(5, 8), fontsize=7, color="#a6e3a1")

        elif self._mode == "AB_TESTING":
            gens_ga, costs_ga = self._ab_data["GA"]
            gens_cso, costs_cso = self._ab_data["CSO"]
            
            all_costs = costs_ga + costs_cso
            if not all_costs:
                self.canvas.draw()
                return

            # Tìm thế hệ cao nhất hiện tại để kéo dài đường line (tránh bị cụt)
            max_gen = 0
            if gens_ga: max_gen = max(max_gen, gens_ga[-1])
            if gens_cso: max_gen = max(max_gen, gens_cso[-1])

            if gens_ga:
                # Kéo dài line GA nếu nó dừng sớm
                display_gens = list(gens_ga)
                display_costs = list(costs_ga)
                if display_gens[-1] < max_gen:
                    display_gens.append(max_gen)
                    display_costs.append(display_costs[-1])
                self.ax.plot(display_gens, display_costs, color="#89b4fa", linewidth=1.8, label="GA")
                
            if gens_cso:
                # Kéo dài line CSO nếu nó dừng sớm
                display_gens = list(gens_cso)
                display_costs = list(costs_cso)
                if display_gens[-1] < max_gen:
                    display_gens.append(max_gen)
                    display_costs.append(display_costs[-1])
                self.ax.plot(display_gens, display_costs, color="#f38ba8", linewidth=1.8, label="CSO")
                
            min_c = min(all_costs)
            max_c = max(all_costs)
            diff = max_c - min_c if max_c > min_c else max_c * 0.1 if max_c > 0 else 1.0
            
            # Tối ưu vùng hiển thị y
            self.ax.set_ylim(max(0, min_c - diff * 0.1), max_c + diff * 0.1)
            self.ax.legend(loc="upper right", fontsize=8, facecolor="#1e1e2e", edgecolor="#45475a", labelcolor="#cdd6f4")

        self.figure.tight_layout()
        self.canvas.draw()
