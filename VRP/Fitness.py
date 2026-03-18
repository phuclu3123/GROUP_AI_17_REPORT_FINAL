"""
vrp/fitness.py
────────────────────────────────────────────────────────────────
FitnessWeights  — Trọng số và mức penalty cho hàm đa mục tiêu
FitnessResult   — Kết quả đánh giá một tuyến đường

Nguyên tắc thiết kế:
  - Layer 2: chỉ phụ thuộc constants, không phụ thuộc domain objects
  - FitnessResult là value object thuần tuý (không có side effect)
  - Tách biệt khỏi logic đánh giá (evaluate nằm trong VRPMapData)
    → dễ thay đổi hàm fitness mà không sửa VRPMapData

Hàm mục tiêu đa tiêu chí:
  F = w_cost x Σcost + w_time x Σtime + w_vehicles x n_vehicles
    + penalty_capacity x Σover_capacity
    + penalty_tw x Σlate_minutes
    + penalty_cargo x n_cargo_violations
    + penalty_vip x n_vip_violations
    + penalty_pair x n_pair_violations
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

from VRP.Constants import (
    W_COST, W_TIME, W_VEHICLES,
    PENALTY_CAPACITY, PENALTY_TW,
    PENALTY_CARGO, PENALTY_VIP, PENALTY_PAIR,
)


@dataclass
class FitnessWeights:
    """
    Cấu hình trọng số và mức penalty cho hàm fitness đa mục tiêu.

    Trọng số mục tiêu:
      w_cost     : float   Trọng số chi phí di chuyển
      w_time     : float   Trọng số tổng thời gian
      w_vehicles : float   Trọng số số xe sử dụng

    Penalty ràng buộc (cộng thêm vào score khi vi phạm):
      penalty_capacity : float   Chi phí vi phạm tải trọng / đơn vị vượt
      penalty_tw       : float   Chi phí vi phạm time window / phút trễ
      penalty_cargo    : float   Chi phí sai loại hàng / lần vi phạm
      penalty_vip      : float   Chi phí VIP không được phục vụ đúng hạn
      penalty_pair     : float   Chi phí Delivery đến trước Pickup (VRPPD)

    Notes
    -----
    Penalty động: gọi scale_penalties(rate) khi tỷ lệ vi phạm cao
    để GA hội tụ về vùng feasible nhanh hơn.
    """
    w_cost           : float = W_COST
    w_time           : float = W_TIME
    w_vehicles       : float = W_VEHICLES

    penalty_capacity : float = PENALTY_CAPACITY
    penalty_tw       : float = PENALTY_TW
    penalty_cargo    : float = PENALTY_CARGO
    penalty_vip      : float = PENALTY_VIP
    penalty_pair     : float = PENALTY_PAIR

    def scale_penalties(self, violation_rate: float) -> None:
        """
        Tăng penalty theo tỷ lệ vi phạm trong population hiện tại.
        Dùng trong GA để "đẩy" population về vùng feasible.

        Parameters
        ----------
        violation_rate : float   Tỷ lệ chromosome vi phạm (0.0 - 1.0)
                                 Ví dụ: 0.6 → 60% cá thể có vi phạm
        """
        if not (0.0 <= violation_rate <= 1.0):
            raise ValueError(f"violation_rate phải trong [0,1], nhận: {violation_rate}")
        factor = 1.0 + 2.0 * violation_rate
        self.penalty_capacity *= factor
        self.penalty_tw       *= factor

    def reset_penalties(self) -> None:
        """Đặt lại penalty về giá trị mặc định từ constants."""
        self.penalty_capacity = PENALTY_CAPACITY
        self.penalty_tw       = PENALTY_TW
        self.penalty_cargo    = PENALTY_CARGO
        self.penalty_vip      = PENALTY_VIP
        self.penalty_pair     = PENALTY_PAIR


@dataclass
class FitnessResult:
    """
    Kết quả đánh giá fitness của một tuyến đường hoặc toàn bộ solution.

    Attributes
    ----------
    total_cost  : float        Tổng chi phí di chuyển (không tính penalty)
    total_time  : float        Tổng thời gian phục vụ (phút)
    n_vehicles  : int          Số xe được sử dụng
    penalty     : float        Tổng penalty từ mọi vi phạm ràng buộc
    violations  : Dict[str,int]  Chi tiết số lần vi phạm theo loại:
                               'capacity', 'tw', 'cargo', 'vip', 'pair'
    """
    total_cost : float            = 0.0
    total_time : float            = 0.0
    n_vehicles : int              = 0
    penalty    : float            = 0.0
    violations : Dict[str, int]   = field(default_factory=dict)

    # Tính score tổng hợp
    def weighted_score(self, weights: FitnessWeights) -> float:
        """
        Tính score tổng hợp theo trọng số.
        Score càng nhỏ càng tốt (GA minimizes).

        Parameters
        ----------
        weights : FitnessWeights   Cấu hình trọng số

        Returns
        -------
        float   F = w_cost x cost + w_time x time + w_vehicles x n_xe + penalty
        """
        return (
            weights.w_cost     * self.total_cost
          + weights.w_time     * self.total_time
          + weights.w_vehicles * self.n_vehicles
          + self.penalty
        )

    # Tổng hợp nhiều route → một solution

    def __iadd__(self, other: "FitnessResult") -> "FitnessResult":
        """
        Cộng dồn kết quả của một route vào kết quả tổng (solution).
        Dùng: solution_result += route_result

        Parameters
        ----------
        other : FitnessResult   Kết quả của một route đơn lẻ
        """
        self.total_cost += other.total_cost
        self.total_time += other.total_time
        self.n_vehicles += other.n_vehicles
        self.penalty    += other.penalty
        for k, v in other.violations.items():
            self.violations[k] = self.violations.get(k, 0) + v
        return self

    # Kiểm tra tính khả thi
    def is_feasible(self) -> bool:
        """
        True nếu solution không vi phạm bất kỳ ràng buộc cứng nào.
        Tức là penalty = 0.
        """
        return self.penalty == 0.0

    def violation_summary(self) -> str:
        """Chuỗi mô tả ngắn các vi phạm đang xảy ra."""
        if not self.violations:
            return "Không vi phạm"
        parts = [f"{k}×{v}" for k, v in self.violations.items()]
        return " | ".join(parts)

    # Debug
    def __repr__(self) -> str:
        feasible = "✓ feasible" if self.is_feasible() else f"✗ {self.violation_summary()}"
        return (
            f"FitnessResult("
            f"cost={self.total_cost:.1f}, "
            f"time={self.total_time:.1f}min, "
            f"vehicles={self.n_vehicles}, "
            f"penalty={self.penalty:.1f}, "
            f"{feasible})"
        )