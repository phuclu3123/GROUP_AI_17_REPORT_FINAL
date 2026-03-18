"""
vrp/vrp_map_data.py
────────────────────────────────────────────────────────────────
VRPMapData — Class trung tâm của hệ thống VRP.

Nguyên tắc thiết kế:
  - Layer 3: tích hợp tất cả các layer bên dưới
  - Single Responsibility: chỉ quản lý dữ liệu, xây ma trận,
    và đánh giá tuyến đường — KHÔNG có logic GA
  - Fluent builder API: add_node(...).add_vehicle(...).build()
  - MatrixCache ẩn bên trong — bên ngoài chỉ dùng dist()/cost()/lookup()
  - evaluate() trả FitnessResult để GA tổng hợp tự do

Quan hệ với graph layer (STT_1 / STT_2):
  - get_vertex(id) → Vertex (STT_1)
  - get_edges(id)  → List[Edge] (STT_2)
  Hai hàm này dùng cho NetworkFlow, tách biệt khỏi GA.
────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from VRP.Constants    import DEFAULT_COST_PER_KM, DEFAULT_DEPART_HOUR, DEFAULT_SPEED_KMH
from VRP.EdgeClass       import Edge
from VRP.Enums        import CargoType, DistanceMode, NodeRole, Priority
from VRP.Matrix_cache import MatrixCache
from VRP.Node_data    import NodeData
from VRP.Scenario     import TrafficProfile, VRPScenario
from VRP.Utils        import euclidean, haversine_km
from VRP.Vehicle_data import VehicleData
from VRP.VertexClass  import Vertex
from VRP.Fitness      import FitnessResult, FitnessWeights

class VRPMapData:
    """
    Kho dữ liệu trung tâm cho bài toán VRP đa biến thể.

    Luồng sử dụng điển hình:
    ─────────────────────────
        data = (VRPMapData(name="...", scenario=sc, ...)
                .add_depot(...)
                .add_customer(...)
                .add_vehicle(...)
                .build())

        # Trong GA fitness:
        result = data.evaluate(route=[0,1,2,0], vehicle=xe)
        score  = result.weighted_score(data.weights)

        # Trong NetworkFlow:
        v = data.get_vertex(node_id)
        for edge in v.edges:
            ...

    Parameters
    ----------
    name             : str              Tên bài toán (hiển thị)
    distance_mode    : DistanceMode     EUCLIDEAN hoặc HAVERSINE
    cost_per_km      : float            Chi phí mặc định mỗi km
    speed_kmh        : float            Tốc độ mặc định (km/h)
    scenario         : VRPScenario      Feature flags cho biến thể VRP
    fitness_weights  : FitnessWeights   Trọng số hàm fitness
    traffic_profile  : TrafficProfile   Hệ số tắc đường theo giờ
    """

    def __init__(
        self,
        name            : str              = "VRP Instance",
        distance_mode   : DistanceMode     = DistanceMode.EUCLIDEAN,
        cost_per_km     : float            = DEFAULT_COST_PER_KM,
        speed_kmh       : float            = DEFAULT_SPEED_KMH,
        scenario        : VRPScenario      = None,
        fitness_weights : FitnessWeights   = None,
        traffic_profile : TrafficProfile   = None,
    ) -> None:
        self.name          = name
        self.distance_mode = distance_mode
        self.cost_per_km   = cost_per_km
        self.speed_kmh     = speed_kmh
        self.scenario      = scenario        or VRPScenario()
        self.weights       = fitness_weights or FitnessWeights()
        self.traffic       = traffic_profile or TrafficProfile()

        # Dữ liệu thô
        self.nodes   : List[NodeData]    = []
        self.vehicles: List[VehicleData] = []

        # Index nội bộ: node.id → vị trí trong self.nodes
        self._idx    : Dict[int, int]    = {}

        # Cache ma trận (khởi tạo sau build)
        self._cache  : Optional[MatrixCache] = None

        # Vertex / Edge cho NetworkFlow (khởi tạo sau build)
        self._vertices: Dict[int, Vertex] = {}

    # BUILDER API — Thêm node / vehicle (fluent, trả self)
    def add_node(self, node: NodeData) -> "VRPMapData":
        """
        Thêm một NodeData vào bản đồ.
        Gọi build() sau khi đã thêm đủ node và vehicle.

        Parameters
        ----------
        node : NodeData   Node cần thêm (id phải duy nhất)

        Raises
        ------
        ValueError   Nếu id đã tồn tại
        """
        if node.id in self._idx:
            raise ValueError(f"Node id={node.id} đã tồn tại.")
        self._idx[node.id] = len(self.nodes)
        self.nodes.append(node)
        return self

    def add_vehicle(self, vehicle: VehicleData) -> "VRPMapData":
        """
        Thêm một VehicleData vào đội xe.

        Parameters
        ----------
        vehicle : VehicleData   Xe cần thêm
        """
        self.vehicles.append(vehicle)
        return self

    def add_depot(
        self, id: int, name: str, x: float, y: float, address: str = ""
    ) -> "VRPMapData":
        """
        Shortcut: tạo và thêm một Depot.

        Parameters
        ----------
        id, name, x, y : Mã, tên, kinh độ, vĩ độ của kho
        address        : Địa chỉ (tuỳ chọn)
        """
        return self.add_node(NodeData(
            id=id, name=name, x=x, y=y,
            node_role=NodeRole.DEPOT, address=address,
        ))

    def add_customer(
        self,
        id          : int,
        name        : str,
        x           : float,
        y           : float,
        demand      : float,
        cargo_type  : CargoType = CargoType.GENERAL,
        priority    : Priority  = Priority.NORMAL,
        time_window : Optional[Tuple[float, float]] = None,
        service_time: float = 0.0,
        address     : str   = "",
    ) -> "VRPMapData":
        """
        Shortcut: tạo và thêm một Customer.

        Parameters
        ----------
        demand      : float          Lượng hàng cần giao (> 0)
        cargo_type  : CargoType      Loại hàng
        priority    : Priority       Mức ưu tiên phục vụ
        time_window : (float,float)  (sớm, muộn) tính bằng phút từ 0h. Ví dụ (480, 720) = 8h–12h
        service_time: float          Thời gian dừng phục vụ tại điểm (phút)
        """
        return self.add_node(NodeData(
            id=id, name=name, x=x, y=y,
            demand=demand,
            node_role=NodeRole.CUSTOMER,
            cargo_type=cargo_type,
            priority=priority,
            time_window=time_window,
            service_time=service_time,
            address=address,
        ))

    def add_pickup_delivery_pair(
        self,
        pickup_id    : int, pickup_name    : str, pickup_x   : float, pickup_y   : float,
        delivery_id  : int, delivery_name  : str, delivery_x : float, delivery_y : float,
        demand       : float,
        cargo_type   : CargoType = CargoType.GENERAL,
        priority     : Priority  = Priority.NORMAL,
        pickup_tw    : Optional[Tuple[float, float]] = None,
        delivery_tw  : Optional[Tuple[float, float]] = None,
    ) -> "VRPMapData":
        """
        Shortcut VRPPD: tạo và thêm cặp Pickup ↔ Delivery.
        Pickup có demand âm (lấy hàng), Delivery có demand dương (giao hàng).
        pair_id được gán tự động để hai node liên kết với nhau.

        Parameters
        ----------
        pickup_*   : Thông tin điểm lấy hàng
        delivery_* : Thông tin điểm giao hàng tương ứng
        demand     : float   Lượng hàng (dương; Pickup dùng -demand)
        """
        self.add_node(NodeData(
            id=pickup_id, name=pickup_name, x=pickup_x, y=pickup_y,
            demand=-abs(demand),
            node_role=NodeRole.PICKUP,
            cargo_type=cargo_type, priority=priority,
            time_window=pickup_tw, pair_id=delivery_id,
        ))
        self.add_node(NodeData(
            id=delivery_id, name=delivery_name, x=delivery_x, y=delivery_y,
            demand=abs(demand),
            node_role=NodeRole.DELIVERY,
            cargo_type=cargo_type, priority=priority,
            time_window=delivery_tw, pair_id=pickup_id,
        ))
        return self


    # BUILD — Tính ma trận & chuẩn bị graph
    def build(self) -> "VRPMapData":
        """
        Tính ba ma trận (dist, cost, time) và xây dựng Vertex+Edge.
        Gọi một lần sau khi thêm đủ node và vehicle.

        Side effects:
          - Khởi tạo self._cache (MatrixCache)
          - Khởi tạo self._vertices (dict id → Vertex)
          - Gán Edge vào từng Vertex

        Returns
        -------
        self   (fluent, dùng được cuối chuỗi builder)
        """
        n  = len(self.nodes)
        t0 = time.perf_counter()

        dist  = np.zeros((n, n), dtype=np.float64)
        cost  = np.zeros((n, n), dtype=np.float64)
        tmat  = np.zeros((n, n), dtype=np.float64)

        for i, ni in enumerate(self.nodes):
            for j, nj in enumerate(self.nodes):
                if i == j:
                    continue
                d         = self._calc_distance(ni, nj)
                dist[i,j] = d
                cost[i,j] = d * self.cost_per_km
                tmat[i,j] = (d / self.speed_kmh) * 60.0   # phút

        elapsed      = time.perf_counter() - t0
        self._cache  = MatrixCache(
            node_ids      = [nd.id for nd in self.nodes],
            dist_matrix   = dist,
            cost_matrix   = cost,
            time_matrix   = tmat,
            build_time_sec= elapsed,
        )

        # Xây Vertex (STT_1) và Edge (STT_2) cho NetworkFlow
        self._vertices = {nd.id: nd.to_vertex() for nd in self.nodes}
        for i, ni in enumerate(self.nodes):
            for j, nj in enumerate(self.nodes):
                if i == j:
                    continue
                edge = Edge(
                    source   = self._vertices[ni.id],
                    target   = self._vertices[nj.id],
                    capacity = float("inf"),
                    cost     = float(cost[i, j]),
                )
                edge.distance    = float(dist[i, j])
                edge.travel_time = float(tmat[i, j])
                self._vertices[ni.id].add_edge(edge)

        print(
            f"[VRPMapData] '{self.name}' | {n} nodes | "
            f"{len(self.vehicles)} vehicles | "
            f"build={elapsed*1000:.2f}ms | {self.scenario.describe()}"
        )
        return self

    # CACHE LOOKUP — API chính cho GA fitness
    def dist(self, id1: int, id2: int) -> float:
        """Khoảng cách (km) từ node id1 → id2. O(1)."""
        return self._cache.dist(id1, id2)

    def cost(self, id1: int, id2: int) -> float:
        """Chi phí từ node id1 → id2. O(1)."""
        return self._cache.cost(id1, id2)

    def time_min(
        self,
        id1         : int,
        id2         : int,
        depart_hour : float     = DEFAULT_DEPART_HOUR,
        cargo       : CargoType = CargoType.GENERAL,
    ) -> float:
        """
        Thời gian di chuyển (phút) từ id1 → id2.
        Có tính hệ số traffic (nếu scenario.use_traffic = True)
        và giới hạn tốc độ hàng dễ vỡ (nếu cargo = FRAGILE).

        Parameters
        ----------
        depart_hour : float       Giờ khởi hành (0–24) để tra traffic factor
        cargo       : CargoType   Loại hàng đang chở
        """
        self._ensure_built()
        base = self._cache.time_base(id1, id2)

        if self.scenario.use_traffic:
            base *= self.traffic.factor_at(depart_hour)

        if cargo == CargoType.FRAGILE:
            base *= 1.1   # buffer 10% cho hàng dễ vỡ

        return base

    def lookup(self, id1: int, id2: int) -> Tuple[float, float, float]:
        """
        Tra nhanh (dist_km, cost, time_base_min) — hot path GA.
        Kết quả được cache sau lần đầu tra.

        Returns
        -------
        Tuple[float, float, float]  (khoảng cách, chi phí, thời gian cơ bản)
        """
        self._ensure_built()
        return self._cache.lookup(id1, id2)

    # EVALUATE — Đánh giá một tuyến đường (dùng trong GA)
    def evaluate(
        self,
        route       : List[int],
        vehicle     : VehicleData,
        depart_hour : float = DEFAULT_DEPART_HOUR,
    ) -> FitnessResult:
        """
        Đánh giá một tuyến đường và trả FitnessResult chi tiết.

        Kiểm tra tất cả ràng buộc theo scenario flags:
          - Tải trọng (luôn kiểm tra)
          - Time window (nếu use_time_windows)
          - Cargo type (nếu use_cargo_match)
          - VIP deadline (nếu use_priority)
          - Pickup trước Delivery (nếu use_pickup_delivery)
          - OVRP: bỏ đoạn cuối về depot (nếu use_open_route + vehicle.open_route)

        Parameters
        ----------
        route       : List[int]      Danh sách node_id theo thứ tự phục vụ.
                                     Phải bắt đầu và kết thúc bằng depot_id
                                     (trừ OVRP).
        vehicle     : VehicleData    Xe thực hiện tuyến này
        depart_hour : float          Giờ xuất phát (0–24)

        Returns
        -------
        FitnessResult   Chi tiết cost, time, penalty, violations
        """
        self._ensure_built()
        sc  = self.scenario
        w   = self.weights
        res = FitnessResult(n_vehicles=1)

        current_time  = depart_hour * 60.0   # phút từ 0h
        current_load  = 0.0
        visited_pks   : set = set()           # VRPPD: pickup đã qua

        for k in range(len(route) - 1):
            id1, id2 = route[k], route[k + 1]

            # OVRP: bỏ qua đoạn cuối → depot
            if (sc.use_open_route and vehicle.open_route
                    and id2 == vehicle.depot_id
                    and k == len(route) - 2):
                break

            nd2 = self._get_node(id2)

            # ── Cargo type ──
            if sc.use_cargo_match and not nd2.is_depot:
                if not vehicle.can_carry(nd2.cargo_type):
                    res.violations["cargo"] = res.violations.get("cargo", 0) + 1
                    res.penalty += w.penalty_cargo

            # ── Di chuyển ──
            d, c, _ = self.lookup(id1, id2)
            tf       = (self.traffic.factor_at(current_time / 60)
                        if sc.use_traffic else 1.0)
            cargo_m  = nd2.cargo_type if sc.use_cargo_match else CargoType.GENERAL
            t_move   = vehicle.travel_time_min(d, cargo_m, tf)

            res.total_cost += c
            res.total_time += t_move
            current_time   += t_move

            if nd2.is_depot:
                continue

            # ── Time Window ──
            if sc.use_time_windows and nd2.has_time_window:
                if current_time < nd2.tw_early:
                    # Đến sớm → chờ (không vi phạm, chỉ mất thời gian)
                    res.total_time += nd2.tw_early - current_time
                    current_time    = nd2.tw_early
                elif current_time > nd2.tw_late:
                    late_min   = current_time - nd2.tw_late
                    vip_factor = 5 if (nd2.is_vip and sc.use_priority) else 1
                    res.penalty += w.penalty_tw * late_min * vip_factor
                    res.violations["tw"] = res.violations.get("tw", 0) + 1

            # ── Tải trọng ──
            current_load += nd2.demand
            if current_load > vehicle.capacity:
                over = current_load - vehicle.capacity
                res.penalty += w.penalty_capacity * over
                res.violations["capacity"] = res.violations.get("capacity", 0) + 1

            # ── VIP deadline ──
            if sc.use_priority and nd2.is_vip:
                vip_deadline_min = 10.0 * 60   # 10h00 = 600 phút
                if current_time > vip_deadline_min:
                    res.penalty += w.penalty_vip
                    res.violations["vip"] = res.violations.get("vip", 0) + 1

            # ── VRPPD: thứ tự pickup → delivery ──
            if sc.use_pickup_delivery:
                if nd2.is_pickup:
                    visited_pks.add(nd2.id)
                elif nd2.is_delivery:
                    if nd2.pair_id not in visited_pks:
                        res.penalty += w.penalty_pair
                        res.violations["pair"] = res.violations.get("pair", 0) + 1

            # ── Thời gian phục vụ ──
            current_time   += nd2.service_time
            res.total_time += nd2.service_time

        res.total_cost += vehicle.fixed_cost
        return res

    # PERSIST — Lưu / nạp cache
    def save_cache(self, filepath: str) -> None:
        """
        Lưu ma trận cache ra file .npz để tái sử dụng.
        Lần chạy sau gọi load_cache() thay vì build() lại từ đầu.

        Parameters
        ----------
        filepath : str   Đường dẫn file (có hoặc không có đuôi .npz)
        """
        self._ensure_built()
        self._cache.save(filepath)

    def load_cache(self, filepath: str) -> None:
        """
        Nạp cache từ file .npz vào instance hiện tại.
        Cần đảm bảo node_ids khớp với danh sách node đã add.

        Parameters
        ----------
        filepath : str   Đường dẫn file .npz
        """
        self._cache = MatrixCache.load(filepath)

    # NETWORKFLOW — Tương thích STT_1 / STT_2
    def get_vertex(self, node_id: int) -> Vertex:
        """
        Lấy Vertex (STT_1) theo node_id.
        Dùng trong thuật toán NetworkFlow / MaxFlow.

        Parameters
        ----------
        node_id : int   ID của node cần lấy Vertex
        """
        self._ensure_built()
        return self._vertices[node_id]

    def get_edges(self, node_id: int) -> List[Edge]:
        """
        Lấy danh sách Edge (STT_2) xuất phát từ node_id.
        Dùng trong thuật toán NetworkFlow.

        Parameters
        ----------
        node_id : int   ID của node nguồn
        """
        self._ensure_built()
        return self._vertices[node_id].edges

    # QUERY HELPERS — Truy vấn tiện ích
    @property
    def depot(self) -> NodeData:
        """Depot đầu tiên (CVRP/VRPTW/OVRP)."""
        depots = self.depots
        if not depots:
            raise ValueError("Chưa có depot trong VRPMapData.")
        return depots[0]

    @property
    def depots(self) -> List[NodeData]:
        """Tất cả node có role=DEPOT (MDVRP)."""
        return [n for n in self.nodes if n.is_depot]

    @property
    def customers(self) -> List[NodeData]:
        """Tất cả node khách hàng (CUSTOMER + PICKUP + DELIVERY)."""
        return [n for n in self.nodes if not n.is_depot]

    def pickup_delivery_pairs(self) -> List[Tuple[NodeData, NodeData]]:
        """
        Trả danh sách cặp (pickup, delivery) cho VRPPD.
        Mỗi cặp: (NodeData pickup, NodeData delivery).
        """
        pairs = []
        for n in self.nodes:
            if n.is_pickup and n.pair_id is not None and n.pair_id in self._idx:
                pairs.append((n, self._get_node(n.pair_id)))
        return pairs

    def vehicles_for_depot(self, depot_id: int) -> List[VehicleData]:
        """
        MDVRP: lấy danh sách xe thuộc kho depot_id.

        Parameters
        ----------
        depot_id : int   ID của kho cần lọc xe
        """
        return [v for v in self.vehicles if v.depot_id == depot_id]

    def total_demand(self) -> float:
        """Tổng nhu cầu dương của tất cả customer (không tính pickup)."""
        return sum(n.demand for n in self.customers if n.demand > 0)

    def cache_report(self) -> None:
        """In báo cáo hiệu suất MatrixCache."""
        self._ensure_built()
        self._cache.report()

    # INTERNAL
    def _ensure_built(self) -> None:
        """Raise RuntimeError nếu build() chưa được gọi."""
        if self._cache is None:
            raise RuntimeError(
                "Gọi .build() trước khi sử dụng VRPMapData."
            )

    def _get_node(self, node_id: int) -> NodeData:
        """Lấy NodeData theo id (O(1) qua index)."""
        return self.nodes[self._idx[node_id]]

    def _calc_distance(self, a: NodeData, b: NodeData) -> float:
        """Tính khoảng cách giữa hai node theo distance_mode."""
        if self.distance_mode == DistanceMode.HAVERSINE:
            return haversine_km(a.x, a.y, b.x, b.y)
        return euclidean(a.x, a.y, b.x, b.y)

    # SUMMARY
    def summary(self) -> None:
        """In tổng quan bài toán ra console."""
        sep = "=" * 64
        print(f"\n{sep}")
        print(f"  {self.name}")
        print(f"  Scenario : {self.scenario.describe()}")
        print(
            f"  Mode     : {self.distance_mode.value} | "
            f"cost/km={self.cost_per_km} | speed={self.speed_kmh}km/h"
        )
        print(
            f"  Weights  : cost×{self.weights.w_cost} + "
            f"time×{self.weights.w_time} + vehicles×{self.weights.w_vehicles}"
        )
        print(sep)
        n_cust = len([n for n in self.nodes if n.is_customer])
        n_pk   = len([n for n in self.nodes if n.is_pickup])
        n_dl   = len([n for n in self.nodes if n.is_delivery])
        print(
            f"  Nodes   : {len(self.nodes)} total | "
            f"depots={len(self.depots)} | customers={n_cust} | "
            f"pickups={n_pk} | deliveries={n_dl}"
        )
        print(f"  Vehicles: {len(self.vehicles)} | Demand: {self.total_demand():.1f}")

        print(f"\n  {'[NODES]'}")
        for nd in self.nodes:
            tw_str   = (f" TW[{nd.tw_early:.0f}-{nd.tw_late:.0f}]"
                        if nd.has_time_window else "")
            pair_str = f" ↔{nd.pair_id}" if nd.pair_id is not None else ""
            vip_str  = " ★" if nd.is_vip else ""
            print(
                f"    {nd.id:3d} | {nd.name:<22} | "
                f"{nd.node_role.value:<9} | dem={nd.demand:6.1f} | "
                f"{nd.cargo_type.value:<8} | {nd.priority.name:<6}"
                f"{vip_str}{tw_str}{pair_str}"
            )

        print(f"\n  {'[VEHICLES]'}")
        for v in self.vehicles:
            open_tag = " [OPEN]" if v.open_route else ""
            cargos   = ",".join(c.value for c in v.allowed_cargo)
            print(
                f"    {v.id:3d} | {v.name:<16} | cap={v.capacity:5.0f} | "
                f"depot={v.depot_id} | [{cargos}]{open_tag}"
            )

        if self._cache:
            self._cache.report()
        print(f"{sep}\n")

    def __repr__(self) -> str:
        built = "built" if self._cache else "NOT built"
        return (
            f"VRPMapData('{self.name}', "
            f"nodes={len(self.nodes)}, vehicles={len(self.vehicles)}, "
            f"{self.scenario.describe()}, {built})"
        )