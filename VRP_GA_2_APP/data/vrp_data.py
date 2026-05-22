"""
Dữ liệu cho bài toán VRP — 3 bộ dữ liệu:
  1. 15 thành phố Châu Âu  (theo bài viết Medium)
  2. 34 tỉnh/thành Việt Nam (sau sáp nhập 2025)
  3. 22 Quận/Huyện TP. Hồ Chí Minh

Mỗi bộ dữ liệu cung cấp:
  - cities : danh sách tên thành phố
  - coords : dict  {tên: (lat, lon)}
  - depot  : tên thành phố làm depot (điểm xuất phát & kết thúc)
"""

import math, random, csv, os

# ====================================================================
# 1.  15 THÀNH PHỐ CHÂU Âu
# ====================================================================
EUROPE_CITIES = [
    "Lisbon", "Porto", "Madrid", "Barcelona", "Toulouse",
    "Paris", "Strasbourg", "Berlin", "Hamburg", "Frankfurt",
    "Amsterdam", "Ghent", "Brussels", "Milan", "Rome",
]

EUROPE_COORDS = {
    "Lisbon":     (38.7223, -9.1393),
    "Porto":      (41.1579, -8.6291),
    "Madrid":     (40.4168, -3.7038),
    "Barcelona":  (41.3874,  2.1686),
    "Toulouse":   (43.6047,  1.4442),
    "Paris":      (48.8566,  2.3522),
    "Strasbourg": (48.5734,  7.7521),
    "Berlin":     (52.5200, 13.4050),
    "Hamburg":    (53.5511,  9.9937),
    "Frankfurt":  (50.1109,  8.6821),
    "Amsterdam":  (52.3676,  4.9041),
    "Ghent":      (51.0543,  3.7174),
    "Brussels":   (50.8503,  4.3517),
    "Milan":      (45.4642,  9.1900),
    "Rome":       (41.9028, 12.4964),
}

EUROPE_DEPOTS = ["Lisbon", "Rome"]

# ====================================================================
# 2.  34 TỈNH / THÀNH VIỆT NAM
# ====================================================================
VIETNAM_CITIES = [
    "Hà Nội", "TP. Hồ Chí Minh", "Huế", "Hải Phòng", "Đà Nẵng", "Cần Thơ",
    "Cao Bằng", "Lạng Sơn", "Lai Châu", "Điện Biên", "Sơn La",
    "Quảng Ninh", "Thanh Hóa", "Nghệ An", "Hà Tĩnh",
    "Tuyên Quang", "Lào Cai", "Thái Nguyên", "Phú Thọ",
    "Bắc Ninh", "Hưng Yên", "Ninh Bình",
    "Quảng Trị", "Quảng Ngãi", "Khánh Hòa",
    "Gia Lai", "Đắk Lắk", "Lâm Đồng",
    "Đồng Nai", "Tây Ninh",
    "Vĩnh Long", "Đồng Tháp", "Cà Mau", "An Giang",
]

VIETNAM_COORDS = {
    "Hà Nội":          (21.0285, 105.8542),
    "TP. Hồ Chí Minh": (10.8231, 106.6297),
    "Huế":             (16.4637, 107.5909),
    "Hải Phòng":       (20.8449, 106.6881),
    "Đà Nẵng":         (16.0544, 108.2022),
    "Cần Thơ":         (10.0452, 105.7469),
    "Cao Bằng":        (22.6666, 106.2640),
    "Lạng Sơn":        (21.8460, 106.7610),
    "Lai Châu":        (22.3964, 103.4709),
    "Điện Biên":       (21.3860, 103.0230),
    "Sơn La":          (21.3270, 103.9188),
    "Quảng Ninh":      (21.0064, 107.2925),
    "Thanh Hóa":       (19.8067, 105.7852),
    "Nghệ An":         (18.6767, 105.6813),
    "Hà Tĩnh":        (18.3559, 105.8877),
    "Tuyên Quang":     (21.8233, 105.2180),
    "Lào Cai":         (22.4856, 103.9707),
    "Thái Nguyên":     (21.5928, 105.8442),
    "Phú Thọ":         (21.4225, 105.2291),
    "Bắc Ninh":        (21.1861, 106.0763),
    "Hưng Yên":        (20.6464, 106.0511),
    "Ninh Bình":       (20.2506, 105.9745),
    "Quảng Trị":       (16.7500, 107.1850),
    "Quảng Ngãi":      (15.1214, 108.8044),
    "Khánh Hòa":       (12.2388, 109.1967),
    "Gia Lai":         (13.9833, 108.0000),
    "Đắk Lắk":        (12.7100, 108.0378),
    "Lâm Đồng":       (11.9404, 108.4583),
    "Đồng Nai":        (11.0686, 106.8599),
    "Tây Ninh":        (11.3351, 106.0983),
    "Vĩnh Long":       (10.2500, 105.9667),
    "Đồng Tháp":       (10.4500, 105.6333),
    "Cà Mau":          ( 9.1769, 105.1524),
    "An Giang":        (10.5216, 105.1259),
}

VIETNAM_DEPOTS = ["Hà Nội", "TP. Hồ Chí Minh"]

# ====================================================================
# 3.  22 QUẬN / HUYỆN TP. HỒ CHÍ MINH
# ====================================================================
HCMC_CITIES = [
    "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 6",
    "Quận 7", "Quận 8", "Quận 10", "Quận 11", "Quận 12",
    "Bình Thạnh", "Gò Vấp", "Phú Nhuận", "Tân Bình", "Tân Phú",
    "Bình Tân", "Thủ Đức",
    "Củ Chi", "Hóc Môn", "Bình Chánh", "Nhà Bè"
]

HCMC_COORDS = {
    "Quận 1":      (10.7769, 106.7009),
    "Quận 3":      (10.7841, 106.6868),
    "Quận 4":      (10.7578, 106.7013),
    "Quận 5":      (10.7540, 106.6633),
    "Quận 6":      (10.7481, 106.6352),
    "Quận 7":      (10.7340, 106.7218),
    "Quận 8":      (10.7243, 106.6286),
    "Quận 10":     (10.7745, 106.6680),
    "Quận 11":     (10.7629, 106.6502),
    "Quận 12":     (10.8671, 106.6413),
    "Bình Thạnh":  (10.8105, 106.7091),
    "Gò Vấp":      (10.8386, 106.6652),
    "Phú Nhuận":   (10.7990, 106.6821),
    "Tân Bình":    (10.8015, 106.6524),
    "Tân Phú":     (10.7901, 106.6280),
    "Bình Tân":    (10.7652, 106.6040),
    "Thủ Đức":     (10.8494, 106.7560),
    "Củ Chi":       (11.0234, 106.4930),
    "Hóc Môn":     (10.8863, 106.5935),
    "Bình Chánh":  (10.6837, 106.5942),
    "Nhà Bè":      (10.6938, 106.7040),
}

HCMC_DEPOTS = ["Quận 1", "Quận 7"]


# ====================================================================
# HÀM TIỆN ÍCH
# ====================================================================
def haversine(coord1, coord2):
    R = 6371
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

def build_cost_matrix(cities, coords):
    matrix = {}
    for c1 in cities:
        matrix[c1] = {}
        for c2 in cities:
            if c1 == c2:
                matrix[c1][c2] = 0.0
            else:
                matrix[c1][c2] = round(haversine(coords[c1], coords[c2]), 2)
    return matrix

def generate_time_data(cities, depots):
    """Sinh dữ liệu thời gian giả lập."""
    time_windows = {}
    service_times = {}
    for city in cities:
        if city in depots:
            time_windows[city] = (0, 1440) # Mở cửa cả ngày
            service_times[city] = 0
        else:
            ready = random.randint(480, 840) # 8h - 14h
            due = ready + random.randint(60, 240) # +1h đến +4h
            time_windows[city] = (ready, due)
            service_times[city] = random.randint(15, 45) # 15-45 phút
    return time_windows, service_times

# ====================================================================
# HÀM LẤY DỮ LIỆU
# ====================================================================
def get_dataset(name):
    from utils.constants import DATASET_EUROPE, DATASET_VIETNAM, DATASET_HCMC
    if name == DATASET_EUROPE:
        cities, coords, depots = EUROPE_CITIES, EUROPE_COORDS, EUROPE_DEPOTS
    elif name == DATASET_VIETNAM:
        cities, coords, depots = VIETNAM_CITIES, VIETNAM_COORDS, VIETNAM_DEPOTS
    elif name == DATASET_HCMC:
        cities, coords, depots = HCMC_CITIES, HCMC_COORDS, HCMC_DEPOTS
    else:
        raise ValueError(f"Unknown dataset: {name}")

    handling = {city: random.randint(10, 50) for city in cities}
    demands = {city: random.randint(10, 50) if city not in depots else 0 for city in cities}
    cost_matrix = build_cost_matrix(cities, coords)
    time_windows, service_times = generate_time_data(cities, depots)
    
    return cities, coords, depots, cost_matrix, handling, demands, time_windows, service_times

def load_custom_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File không tồn tại: {file_path}")

    cities, coords, handling, demands = [], {}, {}, {}
    depots = []

    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 3: continue
            city = row[0].strip()
            lat, lon = float(row[1]), float(row[2])
            fee = int(row[3]) if len(row) > 3 else random.randint(10, 50)
            demand = int(row[4]) if len(row) > 4 else random.randint(10, 40)
            is_depot = row[5].strip().lower() == "true" if len(row) > 5 else False

            cities.append(city)
            coords[city] = (lat, lon)
            handling[city] = fee
            demands[city] = demand
            if is_depot: depots.append(city)

    if not depots and cities: depots = [cities[0]]
    for d in depots: demands[d] = 0
    
    cost_matrix = build_cost_matrix(cities, coords)
    time_windows, service_times = generate_time_data(cities, depots)
    return cities, coords, depots, cost_matrix, handling, demands, time_windows, service_times
