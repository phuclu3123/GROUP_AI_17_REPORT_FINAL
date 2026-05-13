"""
Fitness — Hàm đánh giá độ phù hợp (fitness) của lời giải.
 
Công thức tính toán:
1. Tổng chi phí (Total Cost) =
   + Tổng quãng đường di chuyển (Travel Distance) — tra numpy matrix O(1)
   + Tổng phí bốc xếp tại các điểm (Handling Fees) — KHÔNG tính depot
   + Phạt vi phạm tải trọng (Capacity Penalty)
   + Phạt vi phạm cửa sổ thời gian (Time Window Penalty) — Soft TW
 
2. Fitness = 1 / Total Cost
 
FIX so với phiên bản cũ:
  - Handling fee: Loại trừ depot ra khỏi vòng tính phí.
  - cost_matrix: Dùng numpy ndarray thay vì dict lồng nhau (nhanh hơn ~10x).
  - Tốc độ xe (SPEED) được tính bằng km/phút nhất quán.
"""
 
from __future__ import annotations
import numpy as np
from typing import Dict, List, Optional, Set, Tuple
 
from ga_core.chromosome import Chromosome
 
 
# Tốc độ xe: 40 km/h = 2/3 km/phút
_SPEED_KM_PER_MIN: float = 40.0 / 60.0
 
 
def evaluate(
    chromosome: Chromosome,
    depots: List[str],
    cost_matrix: np.ndarray,          # numpy thay vì dict
    city_index: Dict[str, int],       # ánh xạ tên → chỉ số trong matrix
    handling_fees: Dict[str, float],
    demands: Dict[str, int],
    max_capacity: int,
    time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
    service_times: Optional[Dict[str, int]] = None,
    use_tw: bool = False,
) -> None:
    """
    Tính fitness cho một chromosome (in-place).
    Hỗ trợ: VRP, CVRP, MDVRP, VRPTW (Soft Time Window).
    """
    routes = chromosome.get_routes(depots, cost_matrix, city_index)
    depot_set: Set[str] = set(depots)
    total_cost: float = 0.0
    total_conflicts: int = 0  # THÊM MỚI: đếm số vi phạm
 
    for route in routes:
        route_demand: int = 0
        current_time: float = 480.0  # 8:00 AM (đơn vị: phút)
        visited_for_fee: Set[str] = set()
 
        for i in range(len(route) - 1):
            c1, c2 = route[i], route[i + 1]
            idx1 = city_index.get(c1, -1)
            idx2 = city_index.get(c2, -1)
 
            if idx1 == -1 or idx2 == -1:
                total_cost += 1e9  # Phạt nặng nếu thành phố không tồn tại
                continue
 
            # ── Travel cost (numpy lookup O(1)) ──────────────────────
            dist = cost_matrix[idx1, idx2]
            total_cost += dist
 
            # ── Handling fee (FIX: chỉ tính khách hàng, không tính depot) ──
            # Tính phí khi đến c2 (điểm đến), bỏ qua depot
            if c2 not in depot_set and c2 not in visited_for_fee:
                total_cost += handling_fees.get(c2, 0.0)
                visited_for_fee.add(c2)
 
            # ── Demand (chỉ cộng khách hàng, không cộng depot) ───────
            if c2 not in depot_set:
                route_demand += demands.get(c2, 0)
 
            # ── Time Window (Soft) ────────────────────────────────────
            if use_tw and time_windows and service_times:
                travel_time = dist / _SPEED_KM_PER_MIN
                current_time += travel_time
 
                if c2 not in depot_set:
                    ready, due = time_windows.get(c2, (0, 1440))
 
                    if current_time < ready:
                        current_time = ready  # Chờ đến giờ mở cửa (không phạt)
 
                    if current_time > due:
                        # Soft TW: phạt tuyến tính theo số phút trễ
                        total_cost += (current_time - due) * 100.0
                        total_conflicts += 1 # Vi phạm thời gian
 
                    current_time += service_times.get(c2, 0)
 
        # ── Capacity Penalty (CVRP) ───────────────────────────────────
        if route_demand > max_capacity:
            overflow = route_demand - max_capacity
            total_cost += 10_000.0 * overflow
            total_conflicts += 1 # Vi phạm tải trọng
 
    chromosome.total_cost = total_cost
    chromosome.fitness = 1.0 / total_cost if total_cost > 0 else 0.0
    chromosome.conflicts = total_conflicts
 
 
def evaluate_population(
    population: List[Chromosome],
    depots: List[str],
    cost_matrix: np.ndarray,
    city_index: Dict[str, int],
    handling_fees: Dict[str, float],
    demands: Dict[str, int],
    max_capacity: int,
    time_windows: Optional[Dict[str, Tuple[int, int]]] = None,
    service_times: Optional[Dict[str, int]] = None,
    use_tw: bool = False,
) -> None:
    """Đánh giá toàn bộ quần thể."""
    for chrom in population:
        evaluate(
            chrom, depots, cost_matrix, city_index,
            handling_fees, demands, max_capacity,
            time_windows, service_times, use_tw,
        )
 
