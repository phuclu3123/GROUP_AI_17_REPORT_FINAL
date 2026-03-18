"""
vrp/vehicle_data.py
────────────────────────────────────────────────────────────────
VehicleData — Dữ liệu một phương tiện vận chuyển.

Nguyên tắc thiết kế:
  - Layer 2: phụ thuộc enums, constants
  - Mọi ràng buộc xe đều tự đánh giá được qua các method
  - VRPMapData không cần biết logic bên trong Vehicle

Biến thể VRP:
  OVRP  : open_route=True   → xe không về depot sau khi giao xong
  MDVRP : depot_id          → xe chỉ xuất phát từ depot này
  Cargo : allowed_cargo     → danh sách CargoType được phép chở
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from VRP.Constants import DEFAULT_SPEED_KMH, DEFAULT_COST_PER_KM
from VRP.Enums import CargoType


@dataclass
class VehicleData:
    """
    Một phương tiện vận chuyển trong bài toán VRP.

    Parameters
    ----------
    id               : int              Mã định danh xe
    name             : str              Tên/biển số xe
    capacity         : float            Tải trọng tối đa (kg, thùng, hoặc đơn vị tuỳ ý)
    speed_kmh        : float            Tốc độ trung bình (km/h)
    cost_per_km      : float            Chi phí mỗi km
    fixed_cost       : float            Chi phí cố định mỗi lần xuất xe
    max_stops        : int              Số điểm tối đa trong một chuyến
    open_route       : bool             OVRP: True → không cần về depot
    depot_id         : int              MDVRP: kho gốc của xe
    allowed_cargo    : List[CargoType]  Danh sách loại hàng được phép chở
    max_speed_fragile: float            Tốc độ tối đa khi chở hàng dễ vỡ (km/h)
    """

    id               : int
    name             : str
    capacity         : float
    speed_kmh        : float            = DEFAULT_SPEED_KMH
    cost_per_km      : float            = DEFAULT_COST_PER_KM
    fixed_cost       : float            = 0.0
    max_stops        : int              = 999
    open_route       : bool             = False
    depot_id         : int              = 0
    allowed_cargo    : List[CargoType]  = field(
        default_factory=lambda: list(CargoType)
    )
    max_speed_fragile: float            = 40.0

    # Ràng buộc cargo
    def can_carry(self, cargo: CargoType) -> bool:
        """
        Kiểm tra xe có được phép chở loại hàng `cargo` không.

        Parameters
        ----------
        cargo : CargoType   Loại hàng cần kiểm tra

        Returns
        -------
        bool   True nếu cargo nằm trong allowed_cargo
        """
        return cargo in self.allowed_cargo

    # Tính thời gian di chuyển
    def effective_speed(self, cargo: CargoType) -> float:
        """
        Tốc độ hiệu dụng có tính đến giới hạn hàng dễ vỡ.

        Hàng FRAGILE yêu cầu lái chậm hơn để tránh vỡ hàng.
        Tốc độ thực = min(speed_kmh, max_speed_fragile).

        Parameters
        ----------
        cargo : CargoType   Loại hàng đang chở

        Returns
        -------
        float   Tốc độ km/h sẽ được dùng
        """
        if cargo == CargoType.FRAGILE:
            return min(self.speed_kmh, self.max_speed_fragile)
        return self.speed_kmh

    def travel_time_min(
        self,
        distance_km    : float,
        cargo          : CargoType = CargoType.GENERAL,
        traffic_factor : float     = 1.0,
    ) -> float:
        """
        Thời gian di chuyển (phút) từ A đến B.

        Công thức: (distance / effective_speed) × 60 × traffic_factor

        Parameters
        ----------
        distance_km    : float        Khoảng cách cần di chuyển (km)
        cargo          : CargoType    Loại hàng đang chở (ảnh hưởng tốc độ)
        traffic_factor : float        Hệ số tắc đường (1.0 = bình thường, 1.8 = kẹt)

        Returns
        -------
        float   Thời gian di chuyển tính bằng phút
        """
        speed = self.effective_speed(cargo)
        if speed <= 0:
            raise ValueError(f"Tốc độ phải > 0, nhận: {speed}")
        return (distance_km / speed) * 60.0 * traffic_factor

    # Tính chi phí
    def route_cost(self, total_distance_km: float) -> float:
        """
        Tổng chi phí cho một tuyến đường.
        Bao gồm chi phí cố định + chi phí theo km.

        Parameters
        ----------
        total_distance_km : float   Tổng khoảng cách tuyến đường (km)

        Returns
        -------
        float   Tổng chi phí
        """
        return self.fixed_cost + total_distance_km * self.cost_per_km

    # Debug
    def __repr__(self) -> str:
        open_tag  = " [OPEN]"  if self.open_route else ""
        cargos    = ",".join(c.value for c in self.allowed_cargo)
        return (
            f"Vehicle({self.id}|{self.name}"
            f"|cap={self.capacity}|depot={self.depot_id}"
            f"|[{cargos}]{open_tag})"
        )