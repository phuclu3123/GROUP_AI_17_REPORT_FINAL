"""
GA Engine — Vòng lặp chính của Giải thuật Di truyền (PyQt6 version).

Pseudocode:
  1. Khởi tạo quần thể ngẫu nhiên.
  2. Đánh giá fitness toàn bộ quần thể.
  3. Lặp cho đến khi đạt ngưỡng dừng:
       a. Elitism   : Giữ lại k cá thể tốt nhất.
       b. Selection : Chọn cha mẹ bằng Tournament.
       c. Crossover : OX — kế thừa breaks từ bố/mẹ (không reset).
       d. Mutation  : Swap/Insertion gene + Break mutation.
       e. Evaluate  : Đánh giá thế hệ mới.
       f. Emit signal cập nhật GUI mỗi thế hệ.
  4. Emit finished với routes tốt nhất.

Thay đổi so với phiên bản cũ:
  - Nhận `cost_matrix: np.ndarray` + `city_index: Dict[str, int]`
    thay vì `cost_matrix: Dict[str, Dict[str, float]]`.
  - get_routes() và evaluate_population() đều dùng numpy API mới.
  - Thêm break_mutation_rate để đột biến điểm ngắt (phân bổ xe).
  - Thêm early stopping (patience).
  - Cấu hình được gom vào GAConfig dataclass để dễ truyền từ GUI.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ga_core.chromosome import Chromosome, create_initial_population
from ga_core.crossover import crossover_population
from ga_core.fitness import evaluate_population
from ga_core.mutation import mutate_population
from ga_core.selection import select_parents


class GAEngine(QObject):
    """
    Điều phối thuật toán GA — thiết kế để chạy trên QThread.

    Signals:
        generation_done(gen: int, best_fitness: float, best_cost: float, best_routes: list)
        finished(best_routes: list)
    """

    generation_done = pyqtSignal(int, float, float, int, list)
    finished = pyqtSignal(list)

    def __init__(
        self,
        cities: List[str],
        depots: List[str],
        cost_matrix: np.ndarray,          # THAY ĐỔI: numpy ndarray thay vì dict
        city_index: Dict[str, int],       # THÊM MỚI: ánh xạ tên → chỉ số matrix
        handling_fees: Dict[str, float],
        demands: Dict[str, int],
        max_capacity: int,
        coords: Dict[str, tuple],
        pop_size: int = 100,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.05,
        break_mutation_rate: float = 0.1, # GIẢM VỀ 10% THEO CHUẨN
        generations: int = 300,
        tournament_size: int = 5,
        num_vehicles: int = 3,
        elitism_count: int = 2,
        patience: int = 50,               # THÊM MỚI: early stopping
        time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        service_times: Optional[Dict[str, int]] = None,
        use_tw: bool = False,
    ):
        super().__init__()

        # Dữ liệu bài toán
        self.cities = cities
        self.depots = depots
        self.cost_matrix = cost_matrix
        self.city_index = city_index
        self.handling_fees = handling_fees
        self.demands = demands
        self.max_capacity = max_capacity
        self.coords = coords
        self.time_windows = time_windows
        self.service_times = service_times
        self.use_tw = use_tw

        # Tham số GA
        self.pop_size = pop_size
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.break_mutation_rate = break_mutation_rate
        self.generations = generations
        self.tournament_size = tournament_size
        self.num_vehicles = num_vehicles
        self.elitism_count = elitism_count
        self.patience = patience

        self._stop_flag = False

    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Yêu cầu dừng vòng lặp GA sau thế hệ hiện tại."""
        self._stop_flag = True

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Vòng lặp GA chính. Gọi từ GAWorker.run() trên QThread."""
        self._stop_flag = False

        # ── Bước 1: Khởi tạo quần thể ────────────────────────────────
        population = create_initial_population(
            self.cities, self.depots, self.pop_size, self.num_vehicles
        )

        # ── Bước 2: Đánh giá ban đầu ─────────────────────────────────
        evaluate_population(
            population,
            self.depots,
            self.cost_matrix,
            self.city_index,          # THAY ĐỔI: truyền city_index
            self.handling_fees,
            self.demands,
            self.max_capacity,
            self.time_windows,
            self.service_times,
            self.use_tw,
        )

        best = min(population, key=lambda c: c.total_cost).copy()
        
        # ── Emit Gen 0 (Kết quả khởi tạo ngẫu nhiên) ────────────────
        self.generation_done.emit(
            0, best.fitness, best.total_cost, best.conflicts,
            best.get_routes(self.depots, self.cost_matrix, self.city_index)
        )
        
        no_improve_count = 0

        # ── Bước 3: Vòng lặp tiến hóa ────────────────────────────────
        for gen in range(1, self.generations + 1):
            if self._stop_flag:
                break

            # Nhường CPU cho GUI thread (giữ nguyên từ bản cũ)
            time.sleep(0.001)

            # Sắp xếp tăng dần theo cost (cá thể tốt nhất ở đầu)
            population.sort(key=lambda c: c.total_cost)

            # ── Elitism ──────────────────────────────────────────────
            k = min(self.elitism_count, len(population))
            elites = [population[i].copy() for i in range(k)]

            # ── Selection + Crossover ─────────────────────────────────
            parents = select_parents(
                population,
                count=self.pop_size,
                tournament_size=self.tournament_size,
                method="tournament",
            )
            offspring = crossover_population(parents, self.crossover_rate)

            # ── Reproduction (không qua crossover) ───────────────────
            num_reproduce = max(1, int((1 - self.crossover_rate) * self.pop_size))
            reproduced = select_parents(
                population, num_reproduce, self.tournament_size, method="tournament"
            )

            # ── Gộp thế hệ mới ───────────────────────────────────────
            next_gen = elites + offspring + reproduced

            # Cắt về đúng pop_size
            if len(next_gen) > self.pop_size:
                next_gen = next_gen[: self.pop_size]
            while len(next_gen) < self.pop_size:
                extra = select_parents(population, 1, self.tournament_size)[0]
                next_gen.append(extra)

            # ── Mutation (không mutate elites) ────────────────────────
            non_elite = next_gen[k:]
            non_elite = mutate_population(
                non_elite,
                self.mutation_rate,
                self.break_mutation_rate,   # THÊM MỚI: break mutation
            )
            next_gen = next_gen[:k] + non_elite

            # ── Đánh giá thế hệ mới ──────────────────────────────────
            # Chỉ evaluate cá thể chưa có cost (elites đã có sẵn)
            unevaluated = [c for c in next_gen if c.total_cost == float("inf")]
            evaluate_population(
                unevaluated,
                self.depots,
                self.cost_matrix,
                self.city_index,          # THAY ĐỔI
                self.handling_fees,
                self.demands,
                self.max_capacity,
                self.time_windows,
                self.service_times,
                self.use_tw,
            )

            population = next_gen

            # ── Cập nhật best + Early Stopping ───────────────────────
            gen_best = min(population, key=lambda c: c.total_cost)
            if gen_best.total_cost < best.total_cost:
                best = gen_best.copy()
                no_improve_count = 0
            else:
                no_improve_count += 1

            # ── Emit signal cập nhật GUI ──────────────────────────────
            best_routes = best.get_routes(
                self.depots, self.cost_matrix, self.city_index  # THAY ĐỔI
            )
            self.generation_done.emit(gen, best.fitness, best.total_cost, best.conflicts, best_routes)

            # ── Early Stopping ────────────────────────────────────────
            if no_improve_count >= self.patience:
                # Vẫn emit thế hệ cuối rồi mới thoát
                break

        # ── Kết thúc — trả về lời giải tốt nhất ─────────────────────
        final_routes = best.get_routes(
            self.depots, self.cost_matrix, self.city_index  # THAY ĐỔI
        )
        self.finished.emit(final_routes)


# ======================================================================
class GAWorker(QThread):
    """
    QThread wrapper cho GAEngine.
    Chạy GA ở background thread, forward signals về GUI thread.
    """

    generation_done = pyqtSignal(int, float, float, int, list)
    finished_signal = pyqtSignal(list)

    def __init__(self, engine: GAEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.engine.generation_done.connect(self.generation_done.emit)
        self.engine.finished.connect(self.finished_signal.emit)

    def run(self) -> None:
        self.engine.run()

    def stop(self) -> None:
        self.engine.stop()