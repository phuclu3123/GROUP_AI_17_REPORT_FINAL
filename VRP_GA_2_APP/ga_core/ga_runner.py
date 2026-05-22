"""
GA Runner — Vòng lặp tiến hóa chính.

Tích hợp:
  1. Elitism: Giữ lại k cá thể tốt nhất qua mỗi thế hệ.
  2. Early Stopping: Dừng sớm nếu best fitness không cải thiện sau N thế hệ.
  3. Logging: Ghi lại lịch sử best_cost mỗi thế hệ để vẽ đồ thị hội tụ.

Đây là file "điều phối" — gọi các module selection, crossover, mutation, fitness.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from ga_core.chromosome import Chromosome, create_initial_population
from ga_core.crossover import crossover_population
from ga_core.fitness import (
    DEFAULT_CAPACITY_PENALTY_WEIGHT,
    DEFAULT_INVALID_EDGE_PENALTY,
    DEFAULT_TIME_WINDOW_PENALTY_WEIGHT,
    evaluate_population,
)
from ga_core.mutation import mutate_population
from ga_core.selection import select_parents


# ─────────────────────────────────────────────
# Cấu hình GA
# ─────────────────────────────────────────────
@dataclass
class GAConfig:
    pop_size: int = 100
    num_generations: int = 500
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2
    break_mutation_rate: float = 0.3
    tournament_size: int = 5
    elitism_k: int = 5           # Số cá thể tốt nhất giữ lại
    patience: int = 50           # Early stopping: dừng sau N thế hệ không cải thiện
    selection_method: str = "tournament"
    use_capacity: bool = True
    use_tw: bool = False
    capacity_penalty_weight: float = DEFAULT_CAPACITY_PENALTY_WEIGHT
    time_window_penalty_weight: float = DEFAULT_TIME_WINDOW_PENALTY_WEIGHT
    invalid_edge_penalty: float = DEFAULT_INVALID_EDGE_PENALTY


# ─────────────────────────────────────────────
# Kết quả
# ─────────────────────────────────────────────
@dataclass
class GAResult:
    best_chromosome: Chromosome
    best_cost: float
    history: List[float] = field(default_factory=list)  # best_cost mỗi thế hệ
    generations_run: int = 0
    elapsed_seconds: float = 0.0


# ─────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────
def run_ga(
    cities: List[str],
    depots: List[str],
    cost_matrix: np.ndarray,
    city_index: Dict[str, int],
    handling_fees: Dict[str, float],
    demands: Dict[str, int],
    max_capacity: int,
    num_vehicles: int,
    config: GAConfig = None,
    time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
    service_times: Optional[Dict[str, int]] = None,
) -> GAResult:
    """
    Chạy thuật toán GA cho bài toán VRP/CVRP/MDVRP/VRPTW.

    Args:
        cities: TẤT CẢ thành phố (gồm cả depot).
        depots: Danh sách depot.
        cost_matrix: numpy ndarray [N x N].
        city_index: Dict {tên thành phố → chỉ số trong cost_matrix}.
        handling_fees: Phí bốc xếp tại mỗi thành phố.
        demands: Nhu cầu tại mỗi thành phố.
        max_capacity: Sức chứa tối đa mỗi xe.
        num_vehicles: Số xe.
        config: Cấu hình GA (dùng GAConfig mặc định nếu None).
        time_windows: {city: (ready_time, due_time)} tính bằng phút.
        service_times: {city: service_duration} tính bằng phút.

    Returns:
        GAResult chứa cá thể tốt nhất, lịch sử hội tụ, thời gian chạy.
    """
    if config is None:
        config = GAConfig()

    t_start = time.perf_counter()

    # ── 1. Khởi tạo quần thể ─────────────────────────────────────────
    population = create_initial_population(cities, depots, config.pop_size, num_vehicles)
    evaluate_population(
        population, depots, cost_matrix, city_index,
        handling_fees, demands, max_capacity,
        time_windows, service_times, config.use_tw,
        config.use_capacity,
        config.capacity_penalty_weight,
        config.time_window_penalty_weight,
        config.invalid_edge_penalty,
    )

    best = min(population, key=lambda c: c.total_cost).copy()
    history: List[float] = [best.total_cost]
    no_improve_count = 0

    # ── 2. Vòng lặp tiến hóa ─────────────────────────────────────────
    for gen in range(config.num_generations):

        # Elitism: Lưu k cá thể tốt nhất
        elites = sorted(population, key=lambda c: c.total_cost)[:config.elitism_k]
        elites = [e.copy() for e in elites]

        # Selection
        parents = select_parents(
            population,
            count=config.pop_size,
            tournament_size=config.tournament_size,
            method=config.selection_method,
        )

        # Crossover
        offspring = crossover_population(parents, config.crossover_rate)

        # Mutation
        offspring = mutate_population(
            offspring,
            config.mutation_rate,
            config.break_mutation_rate,
        )

        # Tạo thế hệ mới = offspring + elites (thay thế worst)
        new_population = elites + offspring
        # Giới hạn kích thước quần thể
        while len(new_population) < config.pop_size:
            extra = select_parents(
                population,
                count=1,
                tournament_size=config.tournament_size,
                method=config.selection_method,
            )[0]
            new_population.append(extra)

        # Evaluate thế hệ mới (chỉ evaluate những cá thể chưa có cost)
        unevaluated = [c for c in new_population if c.total_cost == float("inf")]
        evaluate_population(
            unevaluated, depots, cost_matrix, city_index,
            handling_fees, demands, max_capacity,
            time_windows, service_times, config.use_tw,
            config.use_capacity,
            config.capacity_penalty_weight,
            config.time_window_penalty_weight,
            config.invalid_edge_penalty,
        )

        population = sorted(new_population, key=lambda c: c.total_cost)[:config.pop_size]

        # Cập nhật best
        gen_best = min(population, key=lambda c: c.total_cost)
        if gen_best.total_cost < best.total_cost:
            best = gen_best.copy()
            no_improve_count = 0
        else:
            no_improve_count += 1

        history.append(best.total_cost)

        # Early Stopping
        if no_improve_count >= config.patience:
            print(f"[GA] Early stopping at generation {gen + 1} "
                  f"(no improvement for {config.patience} generations).")
            break

    elapsed = time.perf_counter() - t_start
    print(f"[GA] Done. Best objective = {best.total_cost:.2f} | "
          f"Elapsed = {elapsed:.2f}s | Generations = {len(history) - 1}")

    return GAResult(
        best_chromosome=best,
        best_cost=best.total_cost,
        history=history,
        generations_run=len(history) - 1,
        elapsed_seconds=elapsed,
    )
