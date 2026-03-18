"""
vrp/enums.py
────────────────────────────────────────────────────────────────
Tất cả Enum dùng trong hệ thống VRP.

Nguyên tắc thiết kế:
  - Layer 0: không phụ thuộc module nội bộ nào
  - Dùng Enum thay vì string literal → bắt lỗi typo lúc compile
  - Mỗi Enum có docstring mô tả rõ ngữ nghĩa trong bài toán VRP
────────────────────────────────────────────────────────────────
"""

from enum import Enum


class NodeRole(Enum):
    """
    Vai trò của một điểm (node) trong đồ thị VRP.

    DEPOT    → Kho xuất phát / điểm cuối (CVRP, MDVRP)
    CUSTOMER → Khách hàng cần giao hàng (CVRP, VRPTW)
    PICKUP   → Điểm lấy hàng — demand âm (VRPPD)
    DELIVERY → Điểm giao hàng tương ứng pickup — demand dương (VRPPD)
    """
    DEPOT    = "depot"
    CUSTOMER = "customer"
    PICKUP   = "pickup"
    DELIVERY = "delivery"


class CargoType(Enum):
    """
    Loại hàng hoá của một node.
    Quyết định xe nào được phép phục vụ node đó.

    GENERAL  → Hàng thông thường (mọi xe đều chở được)
    COLD     → Hàng lạnh (chỉ xe đông lạnh)
    BULKY    → Hàng cồng kềnh (cần xe tải lớn)
    FRAGILE  → Hàng dễ vỡ (tốc độ bị giới hạn)
    HAZMAT   → Hàng nguy hiểm (xe chuyên dụng có giấy phép)
    """
    GENERAL  = "general"
    COLD     = "cold"
    BULKY    = "bulky"
    FRAGILE  = "fragile"
    HAZMAT   = "hazmat"


class Priority(Enum):
    """
    Mức độ ưu tiên phục vụ của một node.
    Ảnh hưởng đến hệ số penalty khi vi phạm time window.

    NORMAL → Phục vụ theo lịch thông thường
    HIGH   → Ưu tiên, penalty x 2 khi vi phạm TW
    VIP    → Phải phục vụ trước VIP_DEADLINE_HOUR, penalty x 5
    """
    NORMAL = 1
    HIGH   = 2
    VIP    = 3


class DistanceMode(Enum):
    """
    Cách tính khoảng cách giữa hai node.

    EUCLIDEAN  → Khoảng cách phẳng (toạ độ x/y, đơn vị tuỳ ý)
    HAVERSINE  → Khoảng cách vòng cung Trái Đất (lat/lon → km)
    """
    EUCLIDEAN = "euclidean"
    HAVERSINE = "haversine"