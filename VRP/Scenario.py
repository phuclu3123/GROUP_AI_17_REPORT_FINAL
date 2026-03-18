"""
vrp/scenario.py
────────────────────────────────────────────────────────────────
VRPScenario   — Cấu hình bật/tắt các tính năng VRP
TrafficProfile — Hệ số tắc đường theo giờ

Nguyên tắc thiết kế:
  - Layer 2: phụ thuộc constants, không phụ thuộc domain objects
  - VRPScenario là "feature flag" → evaluate() đọc để biết
    cần kiểm tra ràng buộc nào
  - TrafficProfile là pure data + pure function, không có state
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

from VRP.Constants import (
    DEFAULT_PEAK_FACTOR, DEFAULT_OFF_FACTOR, DEFAULT_NIGHT_FACTOR
)


@dataclass
class VRPScenario:
    """
    Feature flags cho bài toán VRP.
    Mỗi flag bật một biến thể hoặc ràng buộc tương ứng.

    Flags biến thể VRP:
      use_time_windows    → VRPTW : kiểm tra time window từng node
      use_multi_depot     → MDVRP : xe xuất phát từ nhiều kho khác nhau
      use_pickup_delivery → VRPPD : ràng buộc pickup phải đến trước delivery
      use_open_route      → OVRP  : xe không cần quay về depot

    Flags ràng buộc thực tế:
      use_traffic         : áp hệ số tắc đường vào travel_time
      use_cargo_match     : kiểm tra xe có đủ điều kiện chở loại hàng không
      use_priority        : tăng penalty cho VIP nếu phục vụ trễ
    """
    use_time_windows    : bool = False
    use_multi_depot     : bool = False
    use_pickup_delivery : bool = False
    use_open_route      : bool = False
    use_traffic         : bool = False
    use_cargo_match     : bool = False
    use_priority        : bool = False

    def describe(self) -> str:
        """
        Trả chuỗi mô tả ngắn gọn scenario đang bật.
        Ví dụ: 'CVRP+VRPTW+Traffic+CargoType'
        """
        labels = {
            "use_time_windows"   : "VRPTW",
            "use_multi_depot"    : "MDVRP",
            "use_pickup_delivery": "VRPPD",
            "use_open_route"     : "OVRP",
            "use_traffic"        : "Traffic",
            "use_cargo_match"    : "CargoType",
            "use_priority"       : "Priority",
        }
        active = [v for k, v in labels.items() if getattr(self, k)]
        return "CVRP+" + "+".join(active) if active else "CVRP"

    def any_active(self) -> bool:
        """True nếu có ít nhất một tính năng nâng cao được bật."""
        return any([
            self.use_time_windows, self.use_multi_depot,
            self.use_pickup_delivery, self.use_open_route,
            self.use_traffic, self.use_cargo_match, self.use_priority,
        ])


@dataclass
class TrafficProfile:
    """
    Hệ số tắc đường theo khung giờ trong ngày.

    Cách dùng:
      factor = profile.factor_at(hour=8.5)   # → 1.8 (peak)
      time_actual = time_base * factor

    Ví dụ TP.HCM:
      peak_slots  = [(7, 9), (17, 19)]   → sáng + chiều kẹt xe
      peak_factor = 1.8                  → chậm hơn 80%
      night_slots = [(22, 24), (0, 5)]   → đêm thông thoáng
      night_factor = 0.7                 → nhanh hơn 30%
    """

    peak_slots   : List[Tuple[int, int]] = field(
        default_factory=lambda: [(7, 9), (17, 19)]
    )
    peak_factor  : float = DEFAULT_PEAK_FACTOR

    off_factor   : float = DEFAULT_OFF_FACTOR

    night_slots  : List[Tuple[int, int]] = field(
        default_factory=lambda: [(22, 24), (0, 5)]
    )
    night_factor : float = DEFAULT_NIGHT_FACTOR

    def factor_at(self, hour: float) -> float:
        """
        Hệ số tắc đường tại giờ `hour` trong ngày.
        Nhân kết quả vào travel_time để ra thời gian thực tế.

        Parameters
        ----------
        hour : float   Giờ trong ngày (0.0–24.0, ví dụ 7.5 = 7h30)

        Returns
        -------
        float   Hệ số: peak_factor | off_factor | night_factor
        """
        h = hour % 24
        for start, end in self.peak_slots:
            if start <= h < end:
                return self.peak_factor
        for start, end in self.night_slots:
            if start <= h < end:
                return self.night_factor
        return self.off_factor

    def describe_hour(self, hour: float) -> str:
        """
        Mô tả trạng thái giao thông tại giờ `hour`.
        Trả 'PEAK' | 'NIGHT' | 'NORMAL'.
        """
        f = self.factor_at(hour)
        if f > self.off_factor:
            return "PEAK"
        if f < self.off_factor:
            return "NIGHT"
        return "NORMAL"

    def daily_schedule(self, step: float = 0.5) -> List[Tuple[float, float, str]]:
        """
        Trả danh sách (hour, factor, label) cho cả ngày.
        Dùng để vẽ biểu đồ traffic factor theo giờ.

        Parameters
        ----------
        step : float   Bước nhảy giờ (0.5 = mỗi 30 phút)
        """
        hours = [i * step for i in range(int(24 / step))]
        return [(h, self.factor_at(h), self.describe_hour(h)) for h in hours]