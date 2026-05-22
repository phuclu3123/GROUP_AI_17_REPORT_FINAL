"""
Hằng số và cấu hình cho ứng dụng VRP-GA.
"""

# ============================================================
# Màu sắc cho từng xe (tối đa 10 xe)
# ============================================================
VEHICLE_COLORS = [
    "#e6194b",  # đỏ
    "#3cb44b",  # xanh lá
    "#4363d8",  # xanh dương
    "#f58231",  # cam
    "#911eb4",  # tím
    "#42d4f4",  # cyan
    "#f032e6",  # hồng
    "#bfef45",  # vàng chanh
    "#fabed4",  # hồng nhạt
    "#469990",  # xanh ngọc
]

# ============================================================
# Tham số GA mặc định
# ============================================================
DEFAULT_POPULATION_SIZE = 100
DEFAULT_CROSSOVER_RATE = 0.8       # r_co
DEFAULT_MUTATION_RATE = 0.05        # r_mu (5% theo chuẩn học thuật)
DEFAULT_GENERATIONS = 300
DEFAULT_TOURNAMENT_SIZE = 5
DEFAULT_NUM_VEHICLES = 3
DEFAULT_ELITISM_COUNT = 2

# ============================================================
# Tên các bộ dữ liệu (dataset)
# ============================================================
DATASET_EUROPE = "15 thành phố Châu Âu"
DATASET_VIETNAM = "34 tỉnh thành Việt Nam"
DATASET_HCMC = "Quận/Huyện TP. Hồ Chí Minh"
