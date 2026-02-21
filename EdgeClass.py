class Edge:
    # Lớp biểu diễn một cạnh trong đồ thị có hướng.
    
    # Hàm khởi tạo cạnh với đỉnh nguồn, đỉnh đích, khả năng thông hành và chi phí
    def __init__(self, source, target, capacity, cost):
        """
        Parameters:
        - source: đỉnh nguồn
        - target: đỉnh đích
        - capacity: khả năng thông hành tối đa
        - cost: chi phí của cạnh
        """
        self.source = source      # Nút nguồn
        self.target = target      # Nút đích
        self.capacity = capacity  # Khả năng thông hành
        self.cost = cost          # Chi phí
        self.flow = 0             # Luồng hiện tại (ban đầu = 0)

    # Tính dung lượng còn lại của cạnh.
    def residual_capacity(self):
        return self.capacity - self.flow

    # Cập nhật luồng hiện tại của cạnh.
    def update_flow(self, value):
        if self.flow + value <= self.capacity:
            self.flow += value
        else:
            raise ValueError("Vượt quá khả năng thông hành")
    
    # Hàm hiển thị thông tin cạnh khi dùng print()
    def __str__(self):
        return f"{self.source} -> {self.target} | cost={self.cost} | flow={self.flow}/{self.capacity}"