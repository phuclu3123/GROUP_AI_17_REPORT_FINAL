import random

# Class Individual

class Individual:
    def __init__(self, num_nodes):
        
        self.num_nodes = num_nodes
        self.route = []       # lộ trình
        self.fitness = None   # tổng khoảng cách

    def create_route(self):
        """
        Tạo route ngẫu nhiên:
        - Bắt đầu từ depot (0)
        - Đi qua các node
        - Quay về depot
        """
        # tạo danh sách node (1 → n-1)
        nodes = list(range(1, self.num_nodes))

        # xáo trộn
        random.shuffle(nodes)

        # tạo route hoàn chỉnh
        self.route = [0] + nodes + [0]

    def calculate_fitness(self, distance_matrix, demands, capacity):
        total_distance = 0
        load = 0
        penalty = 0

        for i in range(len(self.route) - 1):
            from_node = self.route[i]
            to_node = self.route[i + 1]

        # cộng khoảng cách
            total_distance += distance_matrix[from_node][to_node]

            if to_node != 0:
                load += demands[to_node]

                # nếu vượt tải → phạt
                if load > capacity:
                    penalty += 100
            else:
                load = 0  # về depot reset tải

        self.fitness = total_distance + penalty



# Class Population

class Population:
    def __init__(self, size, num_nodes):
        """
        size: số cá thể
        num_nodes: số điểm
        """
        self.size = size
        self.num_nodes = num_nodes
        self.individuals = []

    def initialize(self):
        
        # Khởi tạo quần thể ban đầu
        
        self.individuals = []

        for _ in range(self.size):
            ind = Individual(self.num_nodes)
            ind.create_route()
            self.individuals.append(ind)

    
        
        # Tính fitness cho toàn bộ quần thể
    def evaluate(self, distance_matrix, demands, capacity):
        for ind in self.individuals:
            ind.calculate_fitness(distance_matrix, demands, capacity)

    def get_best(self):
        
       # Lấy cá thể tốt nhất (distance nhỏ nhất)
        
        return min(self.individuals, key=lambda ind: ind.fitness)