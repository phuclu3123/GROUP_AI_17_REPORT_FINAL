import random
from typing import List
from ga_core.chromosome import Chromosome

class Cat(Chromosome):
    """
    Đại diện cho một con Mèo trong thuật toán CSO. Kế thừa Chromosome từ thiết kế GA để tương thích.
    """

    def __init__(self, genes: List[str], num_vehicles: int = 1):
        super().__init__(genes, num_vehicles)
        self.seeking = True 

    def copy(self) -> 'Cat':
        c = Cat(list(self.genes), self.num_vehicles)
        c.breaks = list(self.breaks)
        c.fitness = self.fitness
        c.travel_cost = self.travel_cost
        c.handling_cost = self.handling_cost
        c.penalty_cost = self.penalty_cost
        c.total_cost = self.total_cost
        c.conflicts = self.conflicts
        c.seeking = self.seeking
        return c


def create_initial_swarm(cities: List[str], depot: str, pop_size: int, num_vehicles: int, mixture_ratio: float = 0.5) -> List[Cat]:
    """Tạo quần thể Mèo ban đầu."""
    non_depot = [c for c in cities if c != depot]
    swarm = []
    for _ in range(pop_size):
        genes = list(non_depot)
        random.shuffle(genes)
        cat = Cat(genes, num_vehicles)
        cat.seeking = random.random() < mixture_ratio
        swarm.append(cat)
    return swarm
