"""
Export Service — Hỗ trợ xuất kết quả VRP ra file CSV.
"""

import csv
import os
from typing import List, Dict

def export_to_csv(file_path: str, routes: List[List[str]], route_costs: List[float], route_loads: List[float]):
    """Xuất lộ trình chi tiết ra file CSV."""
    try:
        with open(file_path, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(["Mã Xe", "Lộ trình chi tiết", "Tổng chi phí (km+fee)", "Tổng tải trọng"])
            
            for i in range(len(routes)):
                route_str = " ➔ ".join(routes[i])
                writer.writerow([
                    f"Xe {i+1}",
                    route_str,
                    f"{route_costs[i]:.2f}",
                    f"{route_loads[i]}"
                ])
        return True
    except Exception as e:
        print(f"Export Error: {e}")
        return False
