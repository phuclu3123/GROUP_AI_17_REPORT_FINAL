"""
Crossover — Lai ghép (Order Crossover – OX).

FIX so với phiên bản cũ:
  - Con cái kế thừa breaks từ bố/mẹ thay vì reset về chia đều.
  - Chiến lược kế thừa breaks: Con1 lấy breaks của Parent1, Con2 lấy của Parent2.
    → Thuật toán có thể tiến hóa cả thứ tự thành phố LẪN cách phân bổ xe.
"""

from __future__ import annotations
import random
from typing import List, Tuple

from ga_core.chromosome import Chromosome


def order_crossover(
    parent1: Chromosome,
    parent2: Chromosome,
) -> Tuple[Chromosome, Chromosome]:
    """
    Order Crossover (OX):
      1. Chọn ngẫu nhiên đoạn [start, end) từ parent1 → giữ nguyên trong child1.
      2. Điền phần còn lại từ parent2 theo thứ tự (bỏ trùng).
      3. Tương tự cho child2 (đổi vai trò parent).
      4. FIX: Con kế thừa breaks từ bố/mẹ tương ứng.
    """
    size = len(parent1.genes)
    if size < 2:
        return parent1.copy(), parent2.copy()

    start, end = sorted(random.sample(range(size), 2))

    child1_genes = _ox_build(parent1.genes, parent2.genes, start, end)
    child2_genes = _ox_build(parent2.genes, parent1.genes, start, end)

    # FIX: Truyền breaks của bố/mẹ vào con thay vì để __init__ reset lại
    c1 = Chromosome(child1_genes, parent1.num_vehicles, breaks=list(parent1.breaks))
    c2 = Chromosome(child2_genes, parent2.num_vehicles, breaks=list(parent2.breaks))

    return c1, c2


def _ox_build(p1: List[str], p2: List[str], start: int, end: int) -> List[str]:
    """Build child genes using OX logic."""
    size = len(p1)
    child = [None] * size

    child[start:end] = p1[start:end]
    segment_set = set(p1[start:end])

    remaining = [g for g in p2 if g not in segment_set]

    idx = 0
    for i in range(size):
        if child[i] is None:
            child[i] = remaining[idx]
            idx += 1

    return child


def crossover_population(
    parents: List[Chromosome],
    crossover_rate: float,
) -> List[Chromosome]:
    """
    Thực hiện crossover trên danh sách cha mẹ.
    Số cặp = ceil(crossover_rate * n / 2)
    """
    offspring = []
    n = len(parents)
    num_pairs = max(1, int(crossover_rate * n / 2))

    for _ in range(num_pairs):
        p1, p2 = random.sample(parents, 2)
        c1, c2 = order_crossover(p1, p2)
        offspring.extend([c1, c2])

    return offspring