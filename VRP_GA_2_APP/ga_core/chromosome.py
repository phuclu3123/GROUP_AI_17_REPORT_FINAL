"""
Chromosome — Biểu diễn một lời giải VRP.

Cách mã hóa (Encoding):
1. Một chromosome = mảng numpy hoán vị chỉ số thành phố (không bao gồm depot).
2. Việc chia cho nhiều xe được thực hiện bằng các "điểm ngắt" (break indices).
3. Khi tính toán thực tế, depot sẽ được tự động thêm vào đầu và cuối mỗi đoạn.
   Ví dụ: [A, B, C, D], breaks=[2], 2 xe -> Route 1: Depot-A-B-Depot, Route 2: Depot-C-D-Depot.

FIX so với phiên bản cũ:
  - __init__ nhận tham số `breaks` để con cái kế thừa breaks từ bố/mẹ thay vì tự tạo mới.
  - get_routes: chọn depot tối ưu dựa trên cả điểm đầu VÀ điểm cuối của segment.
  - Dùng numpy array cho genes để tăng hiệu năng.
"""

from __future__ import annotations
import random
import numpy as np
from typing import List, Optional


class Chromosome:
    """Một cá thể (individual) trong quần thể GA cho VRP."""

    def __init__(
        self,
        genes: List[str],
        num_vehicles: int = 1,
        breaks: Optional[List[int]] = None,   # FIX: nhận breaks từ bên ngoài
    ):
        self.genes: List[str] = list(genes)
        self.num_vehicles: int = num_vehicles
        self.fitness: float = 0.0
        self.travel_cost: float = float("inf")
        self.handling_cost: float = 0.0
        self.penalty_cost: float = 0.0
        # Objective used by GA/CSO: travel + handling + penalties.
        self.total_cost: float = float("inf")
        self.conflicts: int = 0  # THÊM MỚI: số lượng vi phạm ràng buộc

        # FIX: Nếu breaks được truyền vào (từ bố/mẹ) thì dùng luôn,
        # chỉ khởi tạo ngẫu nhiên khi tạo cá thể ban đầu.
        if breaks is not None:
            self.breaks: List[int] = self._validate_breaks(breaks, len(genes))
        else:
            self.breaks = self._init_breaks(len(genes), num_vehicles)

    # ------------------------------------------------------------------
    @staticmethod
    def _init_breaks(n: int, num_vehicles: int) -> List[int]:
        """
        Tạo (num_vehicles - 1) break points NGẪU NHIÊN (không chia đều).
        Điều này giúp quần thể ban đầu có tính đa dạng cao hơn.
        """
        if num_vehicles <= 1 or n == 0:
            return []
        # Chọn ngẫu nhiên (num_vehicles - 1) điểm từ [1, n-1]
        if n <= num_vehicles:
            # Không đủ thành phố → chia đều, xe nào thiếu thì rỗng
            return list(range(1, n))[:num_vehicles - 1]
        candidates = random.sample(range(1, n), min(num_vehicles - 1, n - 1))
        return sorted(candidates)

    @staticmethod
    def _validate_breaks(breaks: List[int], n: int) -> List[int]:
        """Đảm bảo breaks hợp lệ: nằm trong (0, n), không trùng nhau."""
        valid = sorted(set(b for b in breaks if 0 < b < n))
        return valid

    # ------------------------------------------------------------------
    def get_routes(
        self,
        depots: List[str],
        cost_matrix: np.ndarray,
        city_index: dict,
    ) -> List[List[str]]:
        """
        Trả về danh sách các route, mỗi route bắt đầu & kết thúc ở depot tối ưu.

        FIX: Chọn depot dựa trên tổng (dist depot→first + dist last→depot)
        thay vì chỉ xét dist depot→first như phiên bản cũ.

        Args:
            depots: Danh sách tên depot.
            cost_matrix: Ma trận numpy [N x N], N = tổng số thành phố + depot.
            city_index: Dict ánh xạ tên thành phố → chỉ số hàng/cột trong cost_matrix.
        """
        all_breaks = [0] + self.breaks + [len(self.genes)]
        routes = []

        for i in range(len(all_breaks) - 1):
            segment = self.genes[all_breaks[i]: all_breaks[i + 1]]
            if not segment:
                continue

            first_city = segment[0]
            last_city = segment[-1]

            # FIX: tìm depot tối ưu dựa trên tổng chi phí vào + ra
            best_depot = depots[0]
            min_cost = float("inf")
            for d in depots:
                d_idx = city_index.get(d)
                f_idx = city_index.get(first_city)
                l_idx = city_index.get(last_city)
                if d_idx is None or f_idx is None or l_idx is None:
                    continue
                # Chi phí: depot → first + last → depot
                round_trip_cost = cost_matrix[d_idx, f_idx] + cost_matrix[l_idx, d_idx]
                if round_trip_cost < min_cost:
                    min_cost = round_trip_cost
                    best_depot = d

            routes.append([best_depot] + segment + [best_depot])

        if not routes:
            routes = [[depots[0], depots[0]]]
        return routes

    # ------------------------------------------------------------------
    def mutate_breaks(self, n: int) -> None:
        """
        FIX (Gemini bỏ sót): Đột biến điểm ngắt để thuật toán có thể
        tiến hóa cách phân bổ khách hàng giữa các xe.
        Dịch chuyển một break point ngẫu nhiên ±1 vị trí.
        """
        if not self.breaks or n < 2:
            return
        idx = random.randrange(len(self.breaks))
        delta = random.choice([-1, 1])
        new_val = self.breaks[idx] + delta

        # Biên an toàn
        lower = self.breaks[idx - 1] if idx > 0 else 0
        upper = self.breaks[idx + 1] if idx < len(self.breaks) - 1 else n

        if lower < new_val < upper:
            self.breaks[idx] = new_val

    # ------------------------------------------------------------------
    def copy(self) -> "Chromosome":
        """Deep copy."""
        c = Chromosome(list(self.genes), self.num_vehicles, list(self.breaks))
        c.fitness = self.fitness
        c.travel_cost = self.travel_cost
        c.handling_cost = self.handling_cost
        c.penalty_cost = self.penalty_cost
        c.total_cost = self.total_cost
        c.conflicts = self.conflicts
        return c

    def __repr__(self) -> str:
        return (
            f"Chromosome(cost={self.total_cost:.1f}, "
            f"fitness={self.fitness:.6f}, breaks={self.breaks})"
        )


# =====================================================================
# HÀM TẠO QUẦN THỂ BAN ĐẦU
# =====================================================================
def create_initial_population(
    cities: List[str],
    depots: List[str],
    pop_size: int,
    num_vehicles: int,
) -> List[Chromosome]:
    """
    Khởi tạo quần thể ban đầu.
    Mỗi cá thể có breaks ngẫu nhiên (không chia đều) để tăng đa dạng.
    """
    non_depot = [c for c in cities if c not in depots]
    population: List[Chromosome] = []

    for _ in range(pop_size):
        genes = list(non_depot)
        random.shuffle(genes)
        # breaks=None → _init_breaks ngẫu nhiên
        chrom = Chromosome(genes, num_vehicles, breaks=None)
        population.append(chrom)

    return population
