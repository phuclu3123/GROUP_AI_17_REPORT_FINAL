"""
vrp/utils.py
────────────────────────────────────────────────────────────────
Hàm tiện ích thuần tuý (pure functions) cho hệ thống VRP.

Nguyên tắc thiết kế:
  - Layer 0: không phụ thuộc module nội bộ nào
  - Tất cả hàm là pure function (không side effect, không state)
  - Dễ unit test độc lập

Hàm:
  haversine_km(lon1, lat1, lon2, lat2) → float
  euclidean(x1, y1, x2, y2)           → float
  minutes_to_hhmm(minutes)            → str
  validate_time_window(tw)            → bool
────────────────────────────────────────────────────────────────
"""

import math
from typing import Optional, Tuple

from VRP.Constants import EARTH_RADIUS_KM

# Khoảng cách
def haversine_km(lon1: float, lat1: float,
                 lon2: float, lat2: float) -> float:
    """
    Tính khoảng cách (km) giữa hai điểm trên bề mặt Trái Đất
    theo công thức Haversine.

    Parameters
    ----------
    lon1, lat1 : float  Kinh độ & vĩ độ điểm A (độ thập phân)
    lon2, lat2 : float  Kinh độ & vĩ độ điểm B (độ thập phân)

    Returns
    -------
    float  Khoảng cách tính bằng km

    Examples
    --------
    >>> haversine_km(106.6745, 10.9804, 106.7044, 10.7769)
    22.86...
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def euclidean(x1: float, y1: float,
              x2: float, y2: float) -> float:
    """
    Khoảng cách Euclid giữa hai điểm (x1,y1) và (x2,y2).
    Dùng khi toạ độ đã là đơn vị phẳng (không phải lat/lon).

    Examples
    --------
    >>> euclidean(0, 0, 3, 4)
    5.0
    """
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


# Hiển thị / Format
def minutes_to_hhmm(minutes: float) -> str:
    """
    Chuyển số phút (tính từ 0h) sang chuỗi HH:MM.

    Examples
    --------
    >>> minutes_to_hhmm(480)
    '08:00'
    >>> minutes_to_hhmm(547.5)
    '09:07'
    """
    total = int(minutes)
    h = (total // 60) % 24
    m = total % 60
    return f"{h:02d}:{m:02d}"


def hhmm_to_minutes(hhmm: str) -> float:
    """
    Chuyển chuỗi 'HH:MM' sang số phút từ 0h.

    Examples
    --------
    >>> hhmm_to_minutes('08:30')
    510.0
    """
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


# Validation
def validate_time_window(tw: Optional[Tuple[float, float]]) -> bool:
    """
    Kiểm tra time window hợp lệ: (early, late) với early < late.

    Returns True nếu tw là None (không có ràng buộc) hoặc hợp lệ.
    Raises ValueError nếu sai format.
    """
    if tw is None:
        return True
    if len(tw) != 2:
        raise ValueError(f"Time window phải là tuple 2 phần tử, nhận: {tw}")
    early, late = tw
    if early >= late:
        raise ValueError(
            f"Time window không hợp lệ: early={early} >= late={late}"
        )
    return True


def validate_demand(demand: float, node_role: str) -> bool:
    """
    Kiểm tra demand hợp lệ theo vai trò node:
      - DEPOT    : phải = 0
      - CUSTOMER : phải > 0
      - PICKUP   : phải < 0 (lấy hàng)
      - DELIVERY : phải > 0 (giao hàng)
    """
    if node_role == "depot" and demand != 0:
        raise ValueError(f"Depot phải có demand=0, nhận demand={demand}")
    if node_role == "customer" and demand <= 0:
        raise ValueError(f"Customer phải có demand>0, nhận demand={demand}")
    if node_role == "pickup" and demand >= 0:
        raise ValueError(f"Pickup phải có demand<0 (âm), nhận demand={demand}")
    if node_role == "delivery" and demand <= 0:
        raise ValueError(f"Delivery phải có demand>0, nhận demand={demand}")
    return True