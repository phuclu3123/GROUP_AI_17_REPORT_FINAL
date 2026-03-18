"""
────────────────────────────────────────────────────────────────
Hằng số toàn cục cho hệ thống VRP.

Nguyên tắc thiết kế:
  - Không import bất kỳ module nội bộ nào (layer 0 — không phụ thuộc)
  - Tất cả giá trị "magic number" đều được đặt tên ở đây
  - Các module khác import từ đây thay vì hard-code số trực tiếp
────────────────────────────────────────────────────────────────
"""

# --- Địa lý ---
EARTH_RADIUS_KM: float = 6371.0        # Bán kính Trái Đất (km)

# --- Giá trị vô cực (thay thế float("inf") để dễ đọc) ---
INF: float = float("inf")

# --- Mặc định bài toán ---
DEFAULT_SPEED_KMH:    float = 60.0     # Tốc độ xe mặc định (km/h)
DEFAULT_COST_PER_KM:  float = 1.0      # Chi phí mỗi km mặc định
DEFAULT_DEPART_HOUR:  float = 8.0      # Giờ xuất phát mặc định (8h sáng)
DEFAULT_SERVICE_TIME: float = 0.0      # Thời gian phục vụ mặc định (phút)

# --- Penalty GA ---
PENALTY_CAPACITY: float = 1_000.0      # Vi phạm tải trọng / đơn vị vượt
PENALTY_TW:       float = 500.0        # Vi phạm time window / phút trễ
PENALTY_CARGO:    float = 2_000.0      # Sai loại hàng / lần
PENALTY_VIP:      float = 3_000.0      # VIP không được phục vụ đúng giờ
PENALTY_PAIR:     float = 5_000.0      # Delivery trước Pickup (VRPPD)

# --- Trọng số fitness mặc định ---
W_COST:     float = 1.0
W_TIME:     float = 0.5
W_VEHICLES: float = 0.3

# --- Traffic ---
DEFAULT_PEAK_FACTOR:  float = 1.8      # Hệ số tắc đường giờ cao điểm
DEFAULT_OFF_FACTOR:   float = 1.0      # Hệ số bình thường
DEFAULT_NIGHT_FACTOR: float = 0.7      # Hệ số đêm (thông thoáng hơn)

# --- VIP time constraint ---
VIP_DEADLINE_HOUR: float = 10.0        # VIP phải phục vụ trước 10h (phút = ×60)

# --- Cache ---
CACHE_EXTENSION: str = ".npz"          # Định dạng lưu cache ma trận