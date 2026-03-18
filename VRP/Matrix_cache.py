"""
vrp/matrix_cache.py
────────────────────────────────────────────────────────────────
MatrixCache — Cache ma trận dist / cost / time cho GA.

Nguyên tắc thiết kế:
  - Layer 1: chỉ phụ thuộc numpy và constants, không phụ thuộc domain
  - Tách biệt hoàn toàn khỏi VRPMapData → dễ test độc lập
  - Hai tầng tra cứu:
      Tầng 1 (nóng) : Python dict (id1,id2) → (d,c,t)
      Tầng 2 (nguồn): NumPy ndarray [n×n]
  - Persist ra .npz để tái sử dụng không tính lại

Tại sao cần cache trong GA?
  - Mỗi thế hệ GA đánh giá hàng nghìn chromosome
  - Mỗi chromosome tính fitness → duyệt nhiều cặp (i,j)
  - Không cache: O(n²) tính lại mỗi lần → bottleneck
  - Có cache: O(1) dict lookup sau lần đầu → tăng tốc ~10x
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

import numpy as np

from VRP.Constants import CACHE_EXTENSION


class MatrixCache:
    """
    Cache hai tầng cho ba ma trận: khoảng cách, chi phí, thời gian.

    Attributes
    ----------
    node_ids       : List[int]      Danh sách ID node theo thứ tự index
    build_time_sec : float          Thời gian build ma trận (giây)

    Internal
    --------
    _id_to_idx   : dict             node_id → vị trí trong ma trận
    _dist/_cost/_time : np.ndarray  Ma trận [nxn] float64
    _pair_cache  : dict             (id1,id2) → (dist, cost, time)
    _stats       : dict             Thống kê hit/miss
    """

    def __init__(
        self,
        node_ids      : List[int],
        dist_matrix   : np.ndarray,
        cost_matrix   : np.ndarray,
        time_matrix   : np.ndarray,
        build_time_sec: float = 0.0,
    ) -> None:
        """
        Parameters
        ----------
        node_ids       : List[int]       ID node theo thứ tự hàng/cột ma trận
        dist_matrix    : ndarray [nxn]   Ma trận khoảng cách (km hoặc đơn vị)
        cost_matrix    : ndarray [nxn]   Ma trận chi phí
        time_matrix    : ndarray [nxn]   Ma trận thời gian (phút, không traffic)
        build_time_sec : float           Thời gian tính toán ma trận (giây)
        """
        self.node_ids       = node_ids
        self.build_time_sec = build_time_sec

        self._id_to_idx : Dict[int, int] = {
            nid: i for i, nid in enumerate(node_ids)
        }
        self._dist = dist_matrix
        self._cost = cost_matrix
        self._time = time_matrix

        # Tầng 1: pair dict cache
        self._pair_cache: Dict[Tuple[int, int], Tuple[float, float, float]] = {}

        # Thống kê hiệu suất
        self._stats = {
            "matrix_reads": 0,
            "pair_hits"   : 0,
            "pair_misses" : 0,
        }

    # Tra cứu đơn (Tầng 2 — numpy)
    def dist(self, id1: int, id2: int) -> float:
        """
        Khoảng cách từ node id1 đến node id2 (km).
        Truy cập trực tiếp numpy matrix — O(1).
        """
        self._stats["matrix_reads"] += 1
        return float(self._dist[self._id_to_idx[id1], self._id_to_idx[id2]])

    def cost(self, id1: int, id2: int) -> float:
        """
        Chi phí di chuyển từ node id1 đến node id2.
        Truy cập trực tiếp numpy matrix — O(1).
        """
        self._stats["matrix_reads"] += 1
        return float(self._cost[self._id_to_idx[id1], self._id_to_idx[id2]])

    def time_base(self, id1: int, id2: int) -> float:
        """
        Thời gian di chuyển cơ bản (phút, chưa áp traffic).
        Truy cập trực tiếp numpy matrix — O(1).
        """
        self._stats["matrix_reads"] += 1
        return float(self._time[self._id_to_idx[id1], self._id_to_idx[id2]])

    # Tra cứu nhanh (Tầng 1 — pair dict)
    def lookup(self, id1: int, id2: int) -> Tuple[float, float, float]:
        """
        Tra nhanh (dist_km, cost, time_min) cho cặp (id1 → id2).

        Lần đầu: đọc từ numpy → lưu vào pair_cache.
        Lần sau: trả trực tiếp từ pair_cache (Python dict lookup).

        Đây là API chính cho vòng lặp fitness GA vì:
          - Hầu hết cặp (i,j) được hỏi nhiều lần qua các thế hệ
          - Dict lookup nhanh hơn numpy index ~3-5× với cặp lặp lại

        Returns
        -------
        Tuple[float, float, float]  (khoảng cách km, chi phí, thời gian phút)
        """
        key = (id1, id2)

        if key in self._pair_cache:
            self._stats["pair_hits"] += 1
            return self._pair_cache[key]

        # Miss → đọc từ numpy và cache lại
        self._stats["pair_misses"] += 1
        i, j = self._id_to_idx[id1], self._id_to_idx[id2]
        val  = (
            float(self._dist[i, j]),
            float(self._cost[i, j]),
            float(self._time[i, j]),
        )
        self._pair_cache[key] = val
        return val

    # Quản lý cache
    def invalidate_pairs(self) -> None:
        """
        Xoá toàn bộ pair cache.
        Dùng khi cost_per_km hoặc speed thay đổi giữa chừng.
        """
        self._pair_cache.clear()
        self._stats["pair_hits"]   = 0
        self._stats["pair_misses"] = 0

    def prewarm(self, id_pairs: List[Tuple[int, int]]) -> None:
        """
        Làm nóng (pre-populate) pair cache với danh sách cặp cho trước.
        Dùng trước khi chạy GA để giảm miss rate trong vòng lặp đầu.

        Parameters
        ----------
        id_pairs : List[Tuple[int,int]]   Các cặp (id1, id2) cần cache trước
        """
        for id1, id2 in id_pairs:
            self.lookup(id1, id2)   # side-effect: nạp vào pair_cache

    # Persist (save / load)
    def save(self, filepath: str) -> None:
        """
        Lưu ba ma trận ra file .npz (nén).
        Lần chạy sau dùng load() thay vì tính lại từ đầu.

        Parameters
        ----------
        filepath : str   Đường dẫn file (có hoặc không có đuôi .npz)
        """
        path = filepath if filepath.endswith(CACHE_EXTENSION) else filepath + CACHE_EXTENSION
        np.savez_compressed(
            path,
            node_ids = np.array(self.node_ids, dtype=np.int64),
            dist     = self._dist,
            cost     = self._cost,
            time     = self._time,
        )
        print(f"[MatrixCache] Đã lưu → {path}")

    @classmethod
    def load(cls, filepath: str) -> "MatrixCache":
        """
        Nạp cache từ file .npz — không tính lại ma trận.

        Parameters
        ----------
        filepath : str   Đường dẫn file .npz

        Returns
        -------
        MatrixCache   Instance mới với ma trận đã nạp sẵn
        """
        path = filepath if filepath.endswith(CACHE_EXTENSION) else filepath + CACHE_EXTENSION
        data = np.load(path)
        instance = cls(
            node_ids    = data["node_ids"].tolist(),
            dist_matrix = data["dist"],
            cost_matrix = data["cost"],
            time_matrix = data["time"],
        )
        print(f"[MatrixCache] Đã nạp ← {path}")
        return instance

    # Debug / Báo cáo
    def report(self) -> None:
        """In thống kê hiệu suất cache ra console."""
        total  = self._stats["pair_hits"] + self._stats["pair_misses"]
        rate   = (self._stats["pair_hits"] / total * 100) if total > 0 else 0.0
        n      = len(self.node_ids)
        cached = len(self._pair_cache)
        print(
            f"  [MatrixCache] {n}×{n} | build={self.build_time_sec*1000:.2f}ms\n"
            f"    matrix_reads : {self._stats['matrix_reads']}\n"
            f"    pair lookups : {total}  (hit={self._stats['pair_hits']},"
            f" miss={self._stats['pair_misses']}, rate={rate:.1f}%)\n"
            f"    pair cached  : {cached}/{n*n} cặp"
        )

    def print_matrix(self, which: str = "dist", max_n: int = 8) -> None:
        """
        In ma trận ra console để debug (cắt bớt nếu lớn hơn max_n).

        Parameters
        ----------
        which : str   'dist' | 'cost' | 'time'
        max_n : int   Số node tối đa hiển thị
        """
        matrices = {"dist": self._dist, "cost": self._cost, "time": self._time}
        if which not in matrices:
            raise ValueError(f"which phải là 'dist'/'cost'/'time', nhận: {which!r}")
        m = matrices[which]
        n = min(len(self.node_ids), max_n)
        ids = self.node_ids[:n]

        header = f"{'':>5}" + "".join(f"{nid:>9}" for nid in ids)
        print(f"\n  Matrix [{which}] ({n}×{n}):")
        print(f"  {header}")
        for i in range(n):
            row = "".join(f"{m[i, j]:9.2f}" for j in range(n))
            print(f"  {ids[i]:>5}{row}")

    def __repr__(self) -> str:
        n = len(self.node_ids)
        return f"MatrixCache(n={n}, cached_pairs={len(self._pair_cache)})"