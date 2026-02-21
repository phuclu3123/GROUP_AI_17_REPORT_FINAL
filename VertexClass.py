class Vertex:
    """
    Lớp biểu diễn một đỉnh trong đồ thị có hướng.
    Mỗi đỉnh có:
    - id: mã định danh duy nhất
    - name: tên hiển thị (không bắt buộc)
    - edges: danh sách các cạnh xuất phát từ đỉnh này
    """
    # Hàm khởi tạo đỉnh với id và tên (tùy chọn)
    def __init__(self, id, name=None):
        """
        Parameters:
        - id (int hoặc str): Mã định danh của đỉnh
        - name (str, optional): Tên hiển thị của đỉnh
        """
        
        # Mã định danh duy nhất của đỉnh
        self.id = id

        # Nếu không truyền name thì tự động đặt tên dạng V1, V2,...
        if name is None:
            self.name = f"V{id}"
        else:
            self.name = name

        # Danh sách các cạnh xuất phát từ đỉnh này
        self.edges = []

    def add_edge(self, edge):
        """
        Thêm một cạnh xuất phát từ đỉnh.
        Parameters:
        - edge: đối tượng Edge
        Chức năng:
        - Lưu cạnh vào danh sách edges
        """
        self.edges.append(edge)

    # Trả về số lượng cạnh xuất phát từ đỉnh.
    def get_degree(self):
        return len(self.edges)
    
    # Hàm hiển thị thông tin đỉnh khi dùng print()
    def __str__(self):
        return f"Vertex ID: {self.id}, Name: {self.name}"
    
    # Hàm biểu diễn đối tượng khi in trong list hoặc debug.
    def __repr__(self):
        return f"Vertex({self.id}, {self.name})"