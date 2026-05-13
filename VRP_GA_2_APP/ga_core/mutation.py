"""
Mutation — Đột biến.

FIX so với phiên bản cũ (điểm Gemini bỏ sót):
  - Thêm đột biến điểm ngắt (break mutation): dịch chuyển break point ±1 vị trí.
    Điều này cho phép thuật toán tiến hóa cách phân bổ khách hàng giữa các xe.
  - mutate_population(): Xen kẽ gene mutation và break mutation.
"""

from __future__ import annotations
import random
from typing import List

from ga_core.chromosome import Chromosome


# ─────────────────────────────────────────────
# Gene Mutations (thứ tự thành phố)
# ─────────────────────────────────────────────

def swap_mutation(chromosome: Chromosome) -> Chromosome:
    """Hoán đổi 2 thành phố ngẫu nhiên trong genes."""
    c = chromosome.copy()
    n = len(c.genes)
    if n < 2:
        return c
    i, j = random.sample(range(n), 2)
    c.genes[i], c.genes[j] = c.genes[j], c.genes[i]
    return c


def inverse_mutation(chromosome: Chromosome) -> Chromosome:
    """Đảo ngược một đoạn con trong genes (2-opt style)."""
    c = chromosome.copy()
    n = len(c.genes)
    if n < 2:
        return c
    i, j = sorted(random.sample(range(n), 2))
    c.genes[i: j + 1] = c.genes[i: j + 1][::-1]
    return c


def insertion_mutation(chromosome: Chromosome) -> Chromosome:
    """
    Insertion Mutation:
    Lấy 1 gene ra khỏi vị trí hiện tại và chèn vào vị trí khác ngẫu nhiên.
    Thường hiệu quả hơn swap cho bài toán routing.
    """
    c = chromosome.copy()
    n = len(c.genes)
    if n < 2:
        return c
    i = random.randrange(n)
    gene = c.genes.pop(i)
    j = random.randrange(len(c.genes) + 1)
    c.genes.insert(j, gene)
    # Cập nhật lại breaks vì độ dài gene không đổi nhưng vị trí dịch
    # (breaks vẫn hợp lệ vì ta không thêm/bớt phần tử)
    return c


# ─────────────────────────────────────────────
# Break Mutation (FIX: điểm Gemini bỏ sót)
# ─────────────────────────────────────────────

def break_mutation(chromosome: Chromosome) -> Chromosome:
    """
    Đột biến điểm ngắt (Break Point Mutation).
    Dịch chuyển một break point ngẫu nhiên ±1 vị trí để thay đổi
    số lượng khách hàng mỗi xe đảm nhận.

    Nếu không có đột biến này, thuật toán CHỈ tối ưu thứ tự thành phố
    mà KHÔNG bao giờ tối ưu được cách phân bổ giữa các xe.
    """
    c = chromosome.copy()
    c.mutate_breaks(len(c.genes))
    return c


# ─────────────────────────────────────────────
# Population-level Mutation
# ─────────────────────────────────────────────

def mutate_population(
    population: List[Chromosome],
    mutation_rate: float,
    break_mutation_rate: float = 0.3,  # 30% mutation sẽ là break mutation
) -> List[Chromosome]:
    """
    Đột biến quần thể:
      - Chọn (mutation_rate * n) cá thể để đột biến gene.
      - Trong đó (break_mutation_rate) tỉ lệ sẽ thực hiện thêm break mutation.

    Args:
        population: Danh sách cá thể.
        mutation_rate: Tỉ lệ cá thể bị đột biến gene.
        break_mutation_rate: Tỉ lệ cá thể bị đột biến break point.
    """
    n = len(population)
    num_mutants = max(1, int(mutation_rate * n))
    indices = random.sample(range(n), min(num_mutants, n))

    for idx in indices:
        # Gene mutation: xen kẽ swap và insertion
        if random.random() < 0.5:
            population[idx] = swap_mutation(population[idx])
        else:
            population[idx] = insertion_mutation(population[idx])

    # Break mutation: áp dụng độc lập với gene mutation
    num_break_mutants = max(1, int(break_mutation_rate * n))
    break_indices = random.sample(range(n), min(num_break_mutants, n))
    for idx in break_indices:
        population[idx] = break_mutation(population[idx])

    return population