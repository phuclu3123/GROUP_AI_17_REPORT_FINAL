"""
vrp/node_data.py
────────────────────────────────────────────────────────────────
NodeData — Dữ liệu một điểm (node) trong bài toán VRP.

Nguyên tắc thiết kế:
  - Layer 2: phụ thuộc enums, constants, utils, vertex
  - Bao (composition) Vertex thay vì kế thừa → tránh ô nhiễm
    interface graph gốc; to_vertex() khi cần dùng NetworkFlow
  - Dùng @dataclass để giảm boilerplate, vẫn thêm được method
  - Validate dữ liệu ngay trong __post_init__

Biến thể VRP được hỗ trợ qua NodeRole:
  DEPOT    → CVRP, MDVRP
  CUSTOMER → CVRP, VRPTW (+ time_window)
  PICKUP   → VRPPD (demand < 0, pair_id → delivery)
  DELIVERY → VRPPD (demand > 0, pair_id → pickup)
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple

from VRP.Enums import CargoType, NodeRole, Priority
from VRP.Utils import validate_demand, validate_time_window, minutes_to_hhmm
from VRP.VertexClass import Vertex


@dataclass
class NodeData:
    """
    Một điểm trong bản đồ VRP.

    Parameters
    ----------
    id           : int              Mã định danh duy nhất
    name         : str              Tên hiển thị
    x            : float            Kinh độ (lon) hoặc toạ độ x
    y            : float            Vĩ độ (lat) hoặc toạ độ y
    demand       : float            Nhu cầu hàng hoá:
                                      > 0 giao hàng (customer/delivery)
                                      < 0 lấy hàng  (pickup)
                                      = 0 depot
    node_role    : NodeRole         Vai trò trong bài toán VRP
    cargo_type   : CargoType        Loại hàng hoá → ràng buộc xe
    priority     : Priority         Mức ưu tiên phục vụ
    time_window  : (float,float)|None  (sớm nhất, muộn nhất) tính bằng phút từ 0h
    service_time : float            Thời gian phục vụ tại điểm (phút)
    pair_id      : int|None         VRPPD: id của điểm đối (pickup↔delivery)
    address      : str              Địa chỉ (tuỳ chọn, không dùng trong tính toán)
    """

    id          : int
    name        : str
    x           : float
    y           : float
    demand      : float                         = 0.0
    node_role   : NodeRole                      = NodeRole.CUSTOMER
    cargo_type  : CargoType                     = CargoType.GENERAL
    priority    : Priority                      = Priority.NORMAL
    time_window : Optional[Tuple[float,float]]  = None
    service_time: float                         = 0.0
    pair_id     : Optional[int]                 = None
    address     : str                           = ""

    def __post_init__(self) -> None:
        """Validate dữ liệu ngay sau khi khởi tạo."""
        validate_time_window(self.time_window)
        # Bỏ validate demand để linh hoạt hơn (depot có thể demand=0)

    
    # Thuộc tính dẫn xuất (không lưu trữ, tính khi cần)
    @property
    def is_depot(self) -> bool:
        """True nếu node là kho xuất phát."""
        return self.node_role == NodeRole.DEPOT

    @property
    def is_customer(self) -> bool:
        """True nếu node là khách hàng thông thường."""
        return self.node_role == NodeRole.CUSTOMER

    @property
    def is_pickup(self) -> bool:
        """True nếu node là điểm lấy hàng (VRPPD)."""
        return self.node_role == NodeRole.PICKUP

    @property
    def is_delivery(self) -> bool:
        """True nếu node là điểm giao hàng tương ứng pickup (VRPPD)."""
        return self.node_role == NodeRole.DELIVERY

    @property
    def is_vip(self) -> bool:
        """True nếu node được đánh dấu VIP (phục vụ ưu tiên cao nhất)."""
        return self.priority == Priority.VIP

    @property
    def has_time_window(self) -> bool:
        """True nếu node có ràng buộc khung giờ phục vụ."""
        return self.time_window is not None

    @property
    def tw_early(self) -> Optional[float]:
        """Thời điểm sớm nhất được phục vụ (phút từ 0h). None nếu không có TW."""
        return self.time_window[0] if self.time_window else None

    @property
    def tw_late(self) -> Optional[float]:
        """Thời điểm muộn nhất được phục vụ (phút từ 0h). None nếu không có TW."""
        return self.time_window[1] if self.time_window else None

    # Chuyển đổi sang graph layer 
    def to_vertex(self) -> Vertex:
        """
        Tạo Vertex (STT_1) từ NodeData để dùng trong NetworkFlow.

        Returns
        -------
        Vertex   Đỉnh có cùng id và name; edges rỗng (gán sau bởi VRPMapData)
        """
        return Vertex(id=self.id, name=self.name)

    # Debug
    def __repr__(self) -> str:
        tw_str   = ""
        if self.time_window:
            tw_str = f" TW[{minutes_to_hhmm(self.tw_early)}-{minutes_to_hhmm(self.tw_late)}]"
        pair_str = f" ↔{self.pair_id}" if self.pair_id is not None else ""
        vip_str  = " ★" if self.is_vip else ""
        return (
            f"Node({self.id}|{self.name}|{self.node_role.value}"
            f"|dem={self.demand}|{self.cargo_type.value}"
            f"|{self.priority.name}{vip_str}{tw_str}{pair_str})"
        )