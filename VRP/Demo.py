"""
demo.py
────────────────────────────────────────────────────────────────
Demo & kiểm thử tích hợp toàn bộ package vrp.

Chạy: python demo.py

Bao gồm:
  1. Khởi tạo bài toán TP.HCM với đầy đủ scenario
  2. Kiểm tra cache lookup + traffic
  3. Đánh giá các tuyến đường với evaluate()
  4. Kiểm tra VRPPD pairs
  5. Kiểm tra NetworkFlow (Vertex / Edge)
  6. Lưu / tải cache
────────────────────────────────────────────────────────────────
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from GROUP_AI_17_REPORT_FINAL.VRP.Matrix_cache import MatrixCache
from VRP import (
    VRPMapData, VRPScenario, TrafficProfile,
    FitnessWeights, NodeData, VehicleData,
    CargoType, Priority, NodeRole, DistanceMode,
    minutes_to_hhmm,
)


def build_hcm_instance() -> VRPMapData:
    """
    Xây dựng bài toán VRP TP.HCM mẫu với đầy đủ biến thể.
    Trả VRPMapData đã build sẵn.
    """
    scenario = VRPScenario(
        use_time_windows    = True,
        use_multi_depot     = True,
        use_pickup_delivery = True,
        use_open_route      = True,
        use_traffic         = True,
        use_cargo_match     = True,
        use_priority        = True,
    )
    weights = FitnessWeights(
        w_cost=1.0, w_time=0.5, w_vehicles=0.3,
        penalty_capacity=1000, penalty_tw=500,
        penalty_cargo=2000, penalty_vip=3000, penalty_pair=5000,
    )
    traffic = TrafficProfile(
        peak_slots=[(7, 9), (17, 19)], peak_factor=1.8,
        night_slots=[(22, 24), (0, 5)], night_factor=0.7,
    )

    data = (
        VRPMapData(
            name           = "TP.HCM — Multi-scenario VRP Demo",
            distance_mode  = DistanceMode.HAVERSINE,
            cost_per_km    = 2.5,
            speed_kmh      = 35.0,
            scenario       = scenario,
            fitness_weights= weights,
            traffic_profile= traffic,
        )
        # MDVRP: 2 kho
        .add_depot(0,  "Kho_BinhDuong", 106.6745, 10.9804)
        .add_depot(10, "Kho_NhaBe",     106.7218, 10.6802)

        # Khách hàng CVRP + VRPTW
        .add_customer(1, "KH_Q1_BenNghe",  106.7044, 10.7769,
                      demand=40, cargo_type=CargoType.GENERAL,
                      priority=Priority.VIP, time_window=(480, 660))
        .add_customer(2, "KH_Q3_VoVanTan", 106.6836, 10.7733,
                      demand=30, cargo_type=CargoType.COLD,
                      time_window=(540, 900))
        .add_customer(3, "KH_Q7_PhuMy",    106.7218, 10.7299,
                      demand=55, cargo_type=CargoType.BULKY,
                      time_window=(600, 960))
        .add_customer(4, "KH_GoVap",       106.6742, 10.8351,
                      demand=28, cargo_type=CargoType.FRAGILE,
                      priority=Priority.HIGH, time_window=(480, 720))
        .add_customer(5, "KH_ThuDuc",      106.7526, 10.8574,
                      demand=50, cargo_type=CargoType.GENERAL,
                      time_window=(600, 1020))

        # VRPPD: cặp pickup + delivery
        .add_pickup_delivery_pair(
            pickup_id=6,   pickup_name="Pickup_TanBinh",
            pickup_x=106.6512, pickup_y=10.7999,
            delivery_id=7, delivery_name="Delivery_BinhThanh",
            delivery_x=106.7134, delivery_y=10.8074,
            demand=20, cargo_type=CargoType.GENERAL,
            pickup_tw=(480, 720), delivery_tw=(540, 900),
        )

        # Xe đa loại, đa kho
        .add_vehicle(VehicleData(
            id=1, name="Tai_5T_BD", capacity=150,
            speed_kmh=35, cost_per_km=3.0, fixed_cost=80,
            depot_id=0,
            allowed_cargo=[CargoType.GENERAL, CargoType.BULKY],
        ))
        .add_vehicle(VehicleData(
            id=2, name="DongLanh_BD", capacity=80,
            speed_kmh=40, cost_per_km=3.5, fixed_cost=100,
            depot_id=0,
            allowed_cargo=[CargoType.COLD, CargoType.FRAGILE],
            max_speed_fragile=30,
        ))
        .add_vehicle(VehicleData(
            id=3, name="Van_NhaBe", capacity=60,
            speed_kmh=45, cost_per_km=2.0, fixed_cost=50,
            depot_id=10, open_route=True,
            allowed_cargo=list(CargoType),
        ))
        .build()
    )
    return data


def demo_cache(data: VRPMapData) -> None:
    print("\n" + "─" * 50)
    print("  [1] Cache lookup")
    print("─" * 50)
    d, c, t = data.lookup(0, 1)
    print(f"  Kho_BD → KH_Q1 : {d:.2f}km | cost={c:.2f} | time_base={t:.1f}min")
    d, c, t = data.lookup(0, 1)   # pair_cache HIT
    print(f"  Kho_BD → KH_Q1 : (CACHE HIT) dist={d:.2f}km")
    data.cache_report()


def demo_traffic(data: VRPMapData) -> None:
    print("\n" + "─" * 50)
    print("  [2] Traffic factor theo giờ")
    print("─" * 50)
    for hour in [6.0, 7.5, 10.0, 14.0, 17.5, 22.5]:
        f     = data.traffic.factor_at(hour)
        label = data.traffic.describe_hour(hour)
        t_min = data.time_min(0, 1, depart_hour=hour)
        print(f"  {hour:5.1f}h → ×{f:.1f} [{label:<6}] time={t_min:.1f}min")


def demo_evaluate(data: VRPMapData) -> None:
    print("\n" + "─" * 50)
    print("  [3] evaluate() — fitness từng tuyến")
    print("─" * 50)

    w = data.weights
    xe1 = data.vehicles[0]   # Tai_5T_BD: chỉ chở GENERAL + BULKY
    xe2 = data.vehicles[1]   # DongLanh_BD: chỉ chở COLD + FRAGILE
    xe3 = data.vehicles[2]   # Van_NhaBe: OPEN route

    # Route 1: Xe tải chở đúng cargo (feasible)
    r1 = [0, 1, 3, 0]   # KH_Q1 (GENERAL/VIP) + KH_Q7 (BULKY)
    res1 = data.evaluate(r1, xe1, depart_hour=8.0)
    print(f"\n  Xe {xe1.name} | route {r1}")
    print(f"    {res1}")
    print(f"    Score: {res1.weighted_score(w):.2f}")

    # Route 2: Xe tải chở sai cargo → vi phạm (COLD)
    r2 = [0, 1, 2, 0]   # KH_Q3 (COLD) nhưng xe chỉ chở GENERAL/BULKY
    res2 = data.evaluate(r2, xe1, depart_hour=8.0)
    print(f"\n  Xe {xe1.name} | route {r2} (có vi phạm cargo)")
    print(f"    {res2}")
    print(f"    Vi phạm: {res2.violations}")

    # Route 3: Xe đông lạnh đúng cargo
    r3 = [0, 2, 4, 0]   # KH_Q3 (COLD) + KH_GoVap (FRAGILE)
    res3 = data.evaluate(r3, xe2, depart_hour=9.0)
    print(f"\n  Xe {xe2.name} | route {r3}")
    print(f"    {res3}")

    # Route 4: OVRP — Van NhaBe không về kho
    r4 = [10, 5, 10]   # xuất phát Kho_NhaBe → KH_ThuDuc → (không về)
    res4 = data.evaluate(r4, xe3, depart_hour=7.5)
    print(f"\n  Xe {xe3.name} [OPEN] | route {r4}")
    print(f"    {res4}")

    # Tổng hợp solution: cộng dồn FitnessResult
    print(f"\n  Tổng solution (r1 + r3 + r4):")
    from VRP.Fitness import FitnessResult
    total = FitnessResult()
    for r in [res1, res3, res4]:
        total += r
    print(f"    {total}")
    print(f"    Score tổng: {total.weighted_score(w):.2f}")


def demo_vrppd(data: VRPMapData) -> None:
    print("\n" + "─" * 50)
    print("  [4] VRPPD pairs")
    print("─" * 50)
    pairs = data.pickup_delivery_pairs()
    print(f"  Số cặp: {len(pairs)}")
    for pickup, delivery in pairs:
        print(f"  {pickup.name} (dem={pickup.demand}) ↔ {delivery.name} (dem={delivery.demand})")


def demo_networkflow(data: VRPMapData) -> None:
    print("\n" + "─" * 50)
    print("  [5] NetworkFlow — Vertex (STT_1) / Edge (STT_2)")
    print("─" * 50)
    v0 = data.get_vertex(0)
    print(f"  {v0}")
    print(f"  Out-degree: {v0.get_degree()}")
    edges = data.get_edges(0)
    for e in edges[:3]:
        print(f"    {e}")
    print(f"  ... ({len(edges)} cạnh tổng cộng)")


def demo_persist(data: VRPMapData) -> None:
    print("\n" + "─" * 50)
    print("  [6] Persist cache")
    print("─" * 50)
    path = "/tmp/vrp_demo_cache"
    data.save_cache(path)

    # Nạp lại
    from VRP.Matrix_cache import MatrixCache
    cache2 = MatrixCache.load(path)
    d, c, t = cache2.lookup(0, 1)
    print(f"  Sau khi load: Kho_BD → KH_Q1 dist={d:.2f}km ✓")


# ──────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 64)
    print("  VRP Package — Demo tích hợp toàn bộ hệ thống")
    print("=" * 64)

    data = build_hcm_instance()
    data.summary()

    demo_cache(data)
    demo_traffic(data)
    demo_evaluate(data)
    demo_vrppd(data)
    demo_networkflow(data)
    demo_persist(data)

    print("\n  ✓ Tất cả demo hoàn thành.\n")