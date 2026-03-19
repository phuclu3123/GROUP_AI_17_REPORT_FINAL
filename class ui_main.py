def load_points_from_file(filename):
    #Đọc file text và trả về list các tuple (x, y).
    #Nếu file không tồn tại, trả về None và in thông báo lỗi.
    if not os.path.exists(filename):
        print(f"Lỗi: File '{filename}' không tồn tại. Hãy chạy phiên bản trước để tạo file dữ liệu.")
        return None

    points = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    x = float(parts[0])
                    y = float(parts[1])
                    points.append((x, y))
    print(f"Đã đọc {len(points)} điểm từ file '{filename}'.")
    return points


def plot_points(points, figsize_inches=(8, 6), dpi=100):
    #Vẽ các điểm dạng chấm tròn với kích thước figure 800x600 pixels.
    x_vals = [p[0] for p in points]
    y_vals = [p[1] for p in points]

    plt.figure(figsize=figsize_inches, dpi=dpi)
    plt.scatter(x_vals, y_vals, color='blue', marker='o', s=50, alpha=0.7, edgecolors='black')

    # Thiết lập giới hạn trục dựa trên dữ liệu (có thể điều chỉnh)
    plt.xlim(min(x_vals) - 5, max(x_vals) + 5)
    plt.ylim(min(y_vals) - 5, max(y_vals) + 5)

    plt.xlabel("Trục X")
    plt.ylabel("Trục Y")
    plt.title(f"Biểu đồ {len(points)} điểm từ file (scene 800x600)")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    FILENAME = "random_data.txt"

    # Đọc dữ liệu từ file (không sinh mới)
    points = load_points_from_file(FILENAME)

    if points is not None:
        plot_points(points)
    else:
        print("Không thể vẽ đồ thị vì thiếu dữ liệu.")
