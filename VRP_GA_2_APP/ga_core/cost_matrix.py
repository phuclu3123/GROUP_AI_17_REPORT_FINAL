"""
Cost Matrix — Xây dựng ma trận chi phí dùng numpy.

Thay vì dùng Dict[str, Dict[str, float]] (chậm, tốn RAM),
ta dùng numpy ndarray [N x N] để tra cứu O(1) với cache locality tốt.

Cung cấp:
  - build_cost_matrix(): Tạo ma trận từ dict cũ (backward compatible).
  - haversine_matrix(): Tạo ma trận từ tọa độ GPS (lat/lon).
"""

from __future__ import annotations
import numpy as np
from typing import Dict, List, Tuple, Optional


def build_cost_matrix(
    cities: List[str],
    dist_dict: Dict[str, Dict[str, float]],
) -> Tuple[np.ndarray, Dict[str, int]]:
    """
    Chuyển đổi dict chi phí cũ sang numpy matrix.

    Args:
        cities: Danh sách TẤT CẢ thành phố (kể cả depot), theo thứ tự cố định.
        dist_dict: Dict lồng nhau {city: {city: distance}}.

    Returns:
        cost_matrix: ndarray shape (N, N), dtype float64.
        city_index: Dict ánh xạ tên thành phố → chỉ số.
    """
    n = len(cities)
    city_index = {c: i for i, c in enumerate(cities)}
    cost_matrix = np.full((n, n), fill_value=np.inf, dtype=np.float64)
    np.fill_diagonal(cost_matrix, 0.0)

    for c1, neighbors in dist_dict.items():
        i = city_index.get(c1)
        if i is None:
            continue
        for c2, dist in neighbors.items():
            j = city_index.get(c2)
            if j is None:
                continue
            cost_matrix[i, j] = dist

    return cost_matrix, city_index


def haversine_matrix(
    cities: List[str],
    coordinates: Dict[str, Tuple[float, float]],  # {city: (lat, lon)}
) -> Tuple[np.ndarray, Dict[str, int]]:
    """
    Tính ma trận khoảng cách Haversine (km) từ tọa độ GPS.
    Dùng vectorized numpy để tính tất cả cặp trong O(N^2) nhưng rất nhanh.

    Args:
        cities: Danh sách thành phố.
        coordinates: Dict {city: (lat_deg, lon_deg)}.

    Returns:
        cost_matrix: ndarray shape (N, N), đơn vị km.
        city_index: Dict ánh xạ tên → chỉ số.
    """
    n = len(cities)
    city_index = {c: i for i, c in enumerate(cities)}

    lats = np.array([np.radians(coordinates[c][0]) for c in cities])
    lons = np.array([np.radians(coordinates[c][1]) for c in cities])

    # Vectorized Haversine
    lat1 = lats[:, None]   # (N, 1)
    lat2 = lats[None, :]   # (1, N)
    lon1 = lons[:, None]
    lon2 = lons[None, :]

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    R = 6371.0  # Bán kính Trái Đất (km)
    cost_matrix = R * c
    np.fill_diagonal(cost_matrix, 0.0)

    return cost_matrix, city_index