import random
# Class cấu hình tham số
class GAConfig:
    def __init__(self):
        self.population_size = 20      # số cá thể
        self.chromosome_length = 10    # số nút giao thông
        self.mutation_rate = 0.1
        self.generations = 50


# Class Genetic Algorithm
class GA:
    def __init__(self, config):
        self.config = config
        self.population = []

    # 1. Khởi tạo quần thể
    def initialize_population(self):
        self.population = []
        for _ in range(self.config.population_size):
            individual = []
            for _ in range(self.config.chromosome_length):
                individual.append(random.randint(0, 1))
            self.population.append(individual)

    # 2. Đánh giá độ thích nghi
    def fitness(self, individual):
        score = sum(individual)
        return score

    def evaluate_population(self):
        fitness_scores = []
        for individual in self.population:
            score = self.fitness(individual)
            fitness_scores.append(score)
        return fitness_scores


if __name__ == "__main__":
    config = GAConfig()
    ga = GA(config)

    ga.initialize_population()
    scores = ga.evaluate_population()

    print("Quần thể ban đầu:")
    for ind in ga.population:
        print(ind)

    print("\nĐộ thích nghi:")
    print(scores)