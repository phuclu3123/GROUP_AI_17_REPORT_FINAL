"""
CSO Engine — Vòng lặp chính của Giải thuật Cat Swarm Optimization (Bầy Mèo).
Phiên bản Discrete CSO để giải bài toán VRP.

Giải thuật Bầy Mèo (CSO) mô phỏng hai hành vi chính của loài mèo:
1. Seeking Mode (Chế độ tìm kiếm): Mèo đang nghỉ ngơi nhưng vẫn quan sát xung quanh (Local Search).
2. Tracing Mode (Chế độ theo dấu): Mèo đang săn mồi và chạy theo con mèo tốt nhất (Global Search).
"""

import random
import time
import numpy as np
from typing import List, Dict
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from cso_core.cat import Cat, create_initial_swarm
# Tái sử dụng hàm đánh giá do cấu trúc route của Cat và Chromosome tương đương nhau
from ga_core.fitness import evaluate

class CSOEngine(QObject):
    """
    Điều phối thuật toán CSO — chạy trên QThread.
    Signals:
        generation_done(int, float, float, list)
        finished(list)
    """

    generation_done = pyqtSignal(int, float, float, int, list)
    finished = pyqtSignal(list)

    def __init__(
        self,
        cities: List[str],
        depots: List[str],
        cost_matrix: "np.ndarray",  # THAY ĐỔI: numpy ndarray
        city_index: dict,           # THÊM MỚI: city_index
        handling_fees: Dict[str, float],
        demands: Dict[str, int],
        max_capacity: int,
        coords: Dict[str, tuple],
        pop_size: int = 100,
        crossover_rate: float = 0.5, # Dùng làm Mixture Ratio (MR) 
        mutation_rate: float = 0.1,  # Dùng làm Seeking Range (SR)
        generations: int = 300,
        tournament_size: int = 5,    # Dùng làm Seeking Memory Pool (SMP)
        num_vehicles: int = 3,
        elitism_count: int = 2,      # Giữ lại n con mèo tốt nhất
        time_windows: dict = None,
        service_times: dict = None,
        use_tw: bool = False
    ):
        super().__init__()
        self.cities = cities
        self.depots = depots
        self.cost_matrix = cost_matrix
        self.city_index = city_index  # LƯU LẠI
        self.handling_fees = handling_fees
        self.demands = demands
        self.max_capacity = max_capacity
        self.coords = coords
        self.time_windows = time_windows
        self.service_times = service_times
        self.use_tw = use_tw

        self.pop_size = pop_size
        self.mr = crossover_rate
        self.sr = mutation_rate
        self.smp = tournament_size
        self.generations = generations
        self.num_vehicles = num_vehicles
        self.elitism_count = elitism_count

        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def _eval_cat(self, cat: Cat):
        from ga_core.fitness import evaluate
        evaluate(
            cat, self.depots, self.cost_matrix, self.city_index, 
            self.handling_fees, self.demands, self.max_capacity, 
            self.time_windows, self.service_times, self.use_tw
        )

    def _seeking_mode(self, cat: Cat) -> Cat:
        """
        Seeking Mode: Mèo nghỉ ngơi nhưng đảo mắt rình rập xung quanh.
        Mô phỏng quá trình tìm kiếm cục bộ (Local Search) xung quanh vị trí hiện tại.
        
        Các tham số chính:
        - SMP (Seeking Memory Pool): Số lượng bản sao được tạo ra để quan sát.
        - SR (Seeking Range): Tỷ lệ biến đổi gene trong mỗi bản sao.
        - SPC (Self Position Considering): Có xem xét vị trí hiện tại hay không.
        """
        pool = []
        for i in range(self.smp):
            copy_cat = cat.copy()
            # SPC (Self position considering) - giữ nguyên 1 bản sao đầu tiên làm gốc
            if i > 0:
                # Đột biến nhẹ: Đổi vị trí gen (SR quyết định số gen được đổi trong Mèo)
                # Giúp mèo khám phá các phương án lân cận tốt hơn.
                num_swaps = max(1, int(len(copy_cat.genes) * self.sr))
                for _ in range(num_swaps):
                    idx1, idx2 = random.sample(range(len(copy_cat.genes)), 2)
                    copy_cat.genes[idx1], copy_cat.genes[idx2] = copy_cat.genes[idx2], copy_cat.genes[idx1]
            
            self._eval_cat(copy_cat)
            pool.append(copy_cat)
        
        # Chọn con mèo có độ thích nghi (Fitness) tốt nhất trong Memory Pool.
        best_candidate = max(pool, key=lambda c: c.fitness)
        return best_candidate

    def _tracing_mode(self, cat: Cat, best_cat: Cat) -> Cat:
        """
        Tracing Mode: Mèo cắm đầu chạy theo con Mèo tốt nhất đàn (Best Cat).
        Mô phỏng quá trình tìm kiếm toàn cục (Global Search) và hội tụ về lời giải tối ưu.
        
        Trong phiên bản Discrete CSO cho VRP, ta sử dụng phép lai Ordered Crossover (OX)
        giữa Mèo hiện tại và Mèo tốt nhất (Best Cat) để tạo ra vị trí mới.
        """
        p1 = cat.genes
        p2 = best_cat.genes
        size = len(p1)
        
        if size < 2: return cat.copy() # Tránh lỗi sample nếu quá ít điểm

        # Chọn một đoạn gene ngẫu nhiên từ mèo hiện tại
        start, end = sorted(random.sample(range(size), 2))
        
        child_genes = [None] * size
        # Giữ nguyên trật tự của đoạn gene đã chọn (Kế thừa kinh nghiệm bản thân)
        child_genes[start:end+1] = p1[start:end+1]
        
        # Điền các vị trí còn lại bằng các node từ Best Cat (Học hỏi từ thủ lĩnh)
        # Đảm bảo không trùng lặp các điểm giao hàng.
        p2_idx = 0
        for i in range(size):
            if child_genes[i] is None:
                while p2[p2_idx] in child_genes:
                    p2_idx += 1
                child_genes[i] = p2[p2_idx]
                
        new_cat = Cat(child_genes, cat.num_vehicles)
        new_cat.breaks = list(cat.breaks)
        self._eval_cat(new_cat)
        return new_cat


    def run(self):
        self._stop_flag = False

        # Khởi tạo quần thể
        # Lọc bỏ các depots khỏi danh sách thành phố để tạo swarm
        non_depot_cities = [c for c in self.cities if c not in self.depots]
        swarm = create_initial_swarm(non_depot_cities, self.depots[0], self.pop_size, self.num_vehicles, self.mr)
        
        # Đánh giá đàn mèo ban đầu
        for cat in swarm:
            self._eval_cat(cat)
            
        # Emit Gen 0
        best_init = max(swarm, key=lambda c: c.fitness)
        self.generation_done.emit(
            0, best_init.fitness, best_init.total_cost, best_init.conflicts,
            best_init.get_routes(self.depots, self.cost_matrix, self.city_index)
        )

        for gen in range(1, self.generations + 1):
            if self._stop_flag:
                break

            time.sleep(0.001)

            # Sắp xếp để tìm Best Cat (Thủ lĩnh)
            swarm.sort(key=lambda c: c.fitness, reverse=True)
            best_cat = swarm[0].copy()
            
            # Elitism: Giữ lại vài con xịn nhất đàn để không mất dấu mục tiêu
            next_generation = [swarm[i].copy() for i in range(min(self.elitism_count, len(swarm)))]

            # Duyệt qua từng con mèo trong đàn (trừ nhóm tinh anh) để cập nhật vị trí
            for cat in swarm[self.elitism_count:]:
                # Dựa vào cờ trạng thái 'seeking' để quyết định hành vi
                if cat.seeking:
                    # Chế độ tìm kiếm cục bộ
                    new_cat = self._seeking_mode(cat)
                else:
                    # Chế độ săn đuổi theo con tốt nhất
                    new_cat = self._tracing_mode(cat, best_cat)
                
                # Cập nhật lại cờ trạng thái cho vòng đời tiếp theo dựa trên MR (Mixture Ratio)
                # MR quyết định tỷ lệ mèo sẽ chuyển sang Seeking Mode.
                new_cat.seeking = random.random() < self.mr
                next_generation.append(new_cat)

            swarm = next_generation

            # Emit signal cho giao diện cập nhật
            best = max(swarm, key=lambda c: c.fitness)
            if best.fitness > best_cat.fitness:
                best_cat = best.copy()

            self.generation_done.emit(
                gen, best_cat.fitness, best_cat.total_cost, best_cat.conflicts,
                best_cat.get_routes(self.depots, self.cost_matrix, self.city_index)
            )

        # Trả về kết quả
        self.finished.emit(best_cat.get_routes(self.depots, self.cost_matrix, self.city_index))


class CSOWorker(QThread):
    generation_done = pyqtSignal(int, float, float, int, list)
    finished_signal = pyqtSignal(list)

    def __init__(self, engine: CSOEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.engine.generation_done.connect(self.generation_done.emit)
        self.engine.finished.connect(self.finished_signal.emit)

    def run(self):
        self.engine.run()

    def stop(self):
        self.engine.stop()
