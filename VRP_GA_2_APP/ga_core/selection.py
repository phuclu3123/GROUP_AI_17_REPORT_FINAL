"""
Selection — Chọn lọc cá thể.

Kết hợp 2 phương pháp:
  1. Tournament Selection (khuyên dùng): Rank-based, không bị ảnh hưởng bởi
     độ chênh lệch fitness cực lớn do hàm phạt nặng gây ra.
  2. Roulette Wheel: Proportional selection, dùng khi hàm phạt nhẹ hoặc fitness
     phân bổ đều.

LÝ DO CHỌN TOURNAMENT CHO BÀI VRP NÀY:
  Hàm phạt tải trọng = 10_000 * overflow có thể tạo ra fitness chênh lệch hàng
  nghìn lần. Với Roulette Wheel, cá thể hợp lệ sẽ "chiếm" gần như 100% xác suất
  được chọn → quần thể hội tụ sớm (premature convergence). Tournament chỉ quan
  tâm "ai cao hơn ai" (so sánh tương đối), nên tránh được vấn đề này.
"""

from __future__ import annotations
import random
from typing import List

from ga_core.chromosome import Chromosome


def tournament_selection(
    population: List[Chromosome],
    tournament_size: int = 5,
) -> Chromosome:
    """
    Tournament Selection:
      Chọn ngẫu nhiên k cá thể → trả về cá thể có fitness cao nhất.
    """
    candidates = random.sample(population, min(tournament_size, len(population)))
    winner = max(candidates, key=lambda c: c.fitness)
    return winner.copy()


def roulette_wheel_selection(population: List[Chromosome]) -> Chromosome:
    """
    Roulette Wheel Selection:
      P(h_i) = Fitness(h_i) / Σ Fitness(h_j)

    Cảnh báo: Nhạy cảm với fitness chênh lệch lớn. Dùng Tournament cho VRP.
    """
    total_fitness = sum(c.fitness for c in population)
    if total_fitness <= 0:
        return random.choice(population).copy()

    pick = random.uniform(0, total_fitness)
    cumulative = 0.0
    for chrom in population:
        cumulative += chrom.fitness
        if cumulative >= pick:
            return chrom.copy()
    return population[-1].copy()


def select_parents(
    population: List[Chromosome],
    count: int,
    tournament_size: int = 5,
    method: str = "tournament",
) -> List[Chromosome]:
    """
    Chọn `count` cha mẹ từ quần thể.

    Args:
        method: "tournament" (khuyên dùng) hoặc "roulette".
    """
    parents = []
    for _ in range(count):
        if method == "roulette":
            parents.append(roulette_wheel_selection(population))
        else:
            parents.append(tournament_selection(population, tournament_size))
    return parents