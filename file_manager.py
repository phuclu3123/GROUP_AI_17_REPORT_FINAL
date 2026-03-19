import random

def generate_random_points(num_points=100, x_range=(0, 100), y_range=(0, 100)):
    Sinh ra num_points điểm với tọa độ (x, y) ngẫu nhiên trong các khoảng cho trước.
    points = []
    for _ in range(num_points):
        x = random.uniform(*x_range)
        y = random.uniform(*y_range)
        points.append((x, y))
    return points

def save_points_to_file(points, filename):
   
    with open(filename, 'w') as f:
        for x, y in points:
            f.write(f"{x} {y}\n")
    print(f"Đã lưu {len(points)} điểm vào file '{filename}'.")

if __name__ == "__main__":
    # Tạo 100 điểm ngẫu nhiên 
    points = generate_random_points(100, (0, 100), (0, 100))
    # Lưu vào file random_data.txt
    save_points_to_file(points, "random_data.txt")
