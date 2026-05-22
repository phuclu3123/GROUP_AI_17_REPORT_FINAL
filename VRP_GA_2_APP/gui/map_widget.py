"""
Map Widget — Hiển thị bản đồ Folium trong QWebEngineView.

- Sử dụng thư viện Folium tạo bản đồ HTML
- Hiển thị Markers cho các thành phố
- Vẽ PolyLine cho routes, mỗi xe một màu khác nhau
- Cập nhật bản đồ real-time mỗi thế hệ GA
"""

import os, tempfile, shutil
import folium
import folium.plugins as plugins
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
from typing import Dict, List
from utils.constants import VEHICLE_COLORS


class MapWidget(QWidget):
    """Widget hiển thị bản đồ Folium qua QWebEngineView."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)

        # Tệp HTML tạm
        self._tmp_dir = tempfile.mkdtemp(prefix="vrp_map_")
        self._html_path = os.path.join(self._tmp_dir, "map.html")
 
    def __del__(self):
        """Dọn dẹp thư mục tạm khi widget bị hủy."""
        try:
            if hasattr(self, '_tmp_dir') and os.path.exists(self._tmp_dir):
                shutil.rmtree(self._tmp_dir)
        except:
            pass

    # -----------------------------------------------------------------
    def show_map(
        self,
        coords: Dict[str, tuple],
        depots: List[str],
        routes: List[List[str]] | None = None,
        generation: int = 0,
        best_cost: float = 0.0,
        best_gen: int = 0,
        blocked_edges: List[tuple] = None,
        is_final: bool = False, # Thêm cờ để tối ưu render
    ):
        """
        Tạo và hiển thị bản đồ Folium.
        """
        # Tính tâm bản đồ
        lats = [c[0] for c in coords.values()]
        lons = [c[1] for c in coords.values()]
        if not lats:
            # Nếu không có điểm nào, mặc định tâm ở Việt Nam hoặc giữ nguyên
            center = [15.8, 108.2] 
            zoom = 6
        else:
            center = [sum(lats) / len(lats), sum(lons) / len(lons)]
            zoom = self._calc_zoom(lats, lons)

        # Tạo bản đồ
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles="OpenStreetMap",
        )

        # ---- Markers ----
        for city, (lat, lon) in coords.items():
            if city in depots:
                # Depot marker — lớn hơn, màu đỏ
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>🏠 DEPOT: {city}</b>",
                    tooltip=f"Warehouse: {city}",
                    icon=folium.Icon(color="red", icon="home", prefix="fa"),
                ).add_to(m)
            else:
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=6,
                    popup=city,
                    tooltip=city,
                    color="#333",
                    fill=True,
                    fill_color="#4363d8",
                    fill_opacity=0.8,
                ).add_to(m)

        # ---- Blocked Edges (Vật cản) ----
        if blocked_edges:
            for (c1, c2) in blocked_edges:
                if c1 in coords and c2 in coords:
                    folium.PolyLine(
                        locations=[coords[c1], coords[c2]],
                        color="#f38ba8", # Red
                        weight=4,
                        dash_array="8, 12",
                        tooltip=f"⛔ CẤM ĐƯỜNG: {c1} ↔ {c2}",
                        popup="Kẹt xe / Tai nạn giao thông"
                    ).add_to(m)

        # ---- Routes (PolyLine) ----
        if routes:
            for idx, route in enumerate(routes):
                color = VEHICLE_COLORS[idx % len(VEHICLE_COLORS)]
                points = []
                for city in route:
                    if city in coords:
                        points.append(coords[city])

                if len(points) >= 2:
                    if is_final:
                        # Bản cuối: dùng AntPath đẹp mắt
                        plugins.AntPath(
                            locations=points, color=color, weight=4, opacity=0.9,
                            delay=800, dash_array=[10, 20], hardware_accelerated=True,
                            tooltip=f"Xe {idx + 1} ({len(route) - 2} điểm)",
                        ).add_to(m)
                    else:
                        # Đang chạy: dùng PolyLine thường cho NHANH
                        folium.PolyLine(
                            locations=points, color=color, weight=3, opacity=0.7,
                            tooltip=f"Xe {idx + 1}",
                        ).add_to(m)

                    # Arrow markers trên route
                    for i, city in enumerate(route):
                        if city not in depots and city in coords:
                            folium.CircleMarker(
                                location=coords[city],
                                radius=7,
                                color=color,
                                fill=True,
                                fill_color=color,
                                fill_opacity=0.9,
                                popup=f"Xe {idx + 1} — {city} (thứ tự: {i})",
                                tooltip=f"{city}",
                            ).add_to(m)

        # ---- Title overlay ----
        title_html = f"""
        <div style="position:fixed; top:10px; left:60px; z-index:9999;
                    background:rgba(255,255,255,0.92); padding:8px 16px;
                    border-radius:8px; font-family:'Segoe UI',Arial,sans-serif;
                    box-shadow:0 2px 8px rgba(0,0,0,0.15);">
            <b style="font-size:14px;">🧬 VRP-GA</b> &nbsp;
            <span style="color:#555;">Thế hệ: <b>{generation}</b></span> &nbsp;
            <span style="color:#e6194b;">Objective: <b>{best_cost:,.1f}</b> (Gen: {best_gen})</span>
        </div>
        """
        m.get_root().html.add_child(folium.Element(title_html))

        # ---- Legend ----
        if routes:
            legend_items = ""
            for idx, route in enumerate(routes):
                c = VEHICLE_COLORS[idx % len(VEHICLE_COLORS)]
                legend_items += (
                    f'<div style="margin:2px 0;"><span style="display:inline-block;'
                    f'width:14px;height:14px;background:{c};border-radius:2px;'
                    f'margin-right:6px;vertical-align:middle;"></span>'
                    f'Xe {idx + 1} ({len(route) - 2} điểm)</div>'
                )

            legend_html = f"""
            <div style="position:fixed; bottom:30px; right:20px; z-index:9999;
                        background:rgba(255,255,255,0.92); padding:10px 14px;
                        border-radius:8px; font-family:'Segoe UI',Arial,sans-serif;
                        font-size:12px; box-shadow:0 2px 8px rgba(0,0,0,0.15);">
                <b>🚗 Chú thích</b><br>{legend_items}
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

        # Lưu & hiển thị — dùng setHtml() với base URL để CDN resources load đúng
        html_string = m.get_root().render()
        self.web_view.setHtml(html_string, QUrl("https://cdn.jsdelivr.net"))

    # -----------------------------------------------------------------
    @staticmethod
    def _calc_zoom(lats, lons):
        """Tính zoom level phù hợp dựa trên phạm vi toạ độ."""
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        spread = max(lat_range, lon_range)
        if spread > 30:
            return 4
        elif spread > 15:
            return 5
        elif spread > 5:
            return 6
        elif spread > 2:
            return 8
        elif spread > 0.5:
            return 10
        else:
            return 12
