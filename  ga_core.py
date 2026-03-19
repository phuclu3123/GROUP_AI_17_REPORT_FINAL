# ga_core.py

from individual import Population

# Class cấu hình GA 

class GAConfig:
    def __init__(self):
        self.population_size = 20      # số cá thể
        self.chromosome_length = 6     # số node (bao gồm depot)
        self.mutation_rate = 0.1
        self.generations = 50


# Class GA chính

class GA:
    def __init__(self, config):
        """
        config: đối tượng GAConfig
        """
        self.config = config

        # tạo quần thể 
        self.population = Population(
            size=config.population_size,
            num_nodes=config.chromosome_length
        )

        # ma trận khoảng cách (demo)
        self.distance_matrix = self.create_distance_matrix()
        # nhu cầu từng node (node 0 = depot)
        self.demands = [0, 2, 3, 4, 2, 1]

        # sức chứa xe
        self.capacity = 5

    def create_distance_matrix(self):
       
        n = self.config.chromosome_length

        # ví dụ đơn giản 
        matrix = [
            [0, 2, 9, 10, 7, 3],
            [2, 0, 6, 4, 3, 8],
            [9, 6, 0, 8, 5, 7],
            [10, 4, 8, 0, 6, 2],
            [7, 3, 5, 6, 0, 4],
            [3, 8, 7, 2, 4, 0]
        ]

        return matrix

    # Khởi tạo quần thể

    def initialize(self):
        """
        Khởi tạo quần thể ban đầu
        """
        self.population.initialize()

   
    # Đánh giá quần thể
    
    def evaluate(self):
        self.population.evaluate(
        self.distance_matrix,
        self.demands,
        self.capacity
    )

    
    # Lấy lời giải tốt nhất
    
    def get_best_solution(self):
        """
        Trả về cá thể có fitness tốt nhất
        """
        return self.population.get_best()

    # Chạy GA 
    
    def run(self):
        
        #Chạy thuật toán GA cơ bản
        
        # bước 1: khởi tạo
        self.initialize()

        # bước 2: đánh giá
        self.evaluate()

        # bước 3: lấy kết quả
        best = self.get_best_solution()

        return best