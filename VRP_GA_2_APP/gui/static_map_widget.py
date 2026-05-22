"""
Static Map Widget — Sơ đồ lộ trình Hình học (Offline).
Sử dụng Matplotlib để vẽ các điểm và đường nối, không cần internet.
"""

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
from utils.constants import VEHICLE_COLORS

class StaticMapWidget(QWidget):
    point_added = pyqtSignal(float, float, bool) # lat, lon, is_depot
    point_removed = pyqtSignal(float, float)     # lat, lon

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 5), dpi=100)
        self.figure.patch.set_facecolor("#1e1e2e")
        self.canvas = FigureCanvasQTAgg(self.figure)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self._init_axes()
        
        # Kết nối sự kiện chuột
        self.canvas.mpl_connect("button_press_event", self._on_click)

    def _on_click(self, event):
        if event.inaxes != self.ax:
            return
        
        # event.xdata là lon, event.ydata là lat (theo cách ta vẽ)
        lon, lat = event.xdata, event.ydata
        
        if event.button == 1: # Chuột trái -> Thêm Khách hàng
            self.point_added.emit(lat, lon, False)
        elif event.button == 3: # Chuột phải -> Thêm Kho hàng
            self.point_added.emit(lat, lon, True)
        elif event.button == 2: # Nút cuộn (giữa) -> XÓA
            self.point_removed.emit(lat, lon)

    def _init_axes(self):
        self.ax.clear()
        self.ax.set_facecolor("#1e1e2e")
        self.ax.set_title("Sơ đồ Lộ trình Hình học (Offline)", color="#cdd6f4", fontsize=10)
        self.ax.tick_params(colors="#a6adc8", labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color("#45475a")
        self.ax.grid(True, alpha=0.1, color="#585b70")
        self.figure.tight_layout()

    def update_plot(self, coords, depots, routes=None):
        self._init_axes()
        if not coords:
            self.canvas.draw()
            return

        # Vẽ các thành phố
        lats = []
        lons = []
        for city, (lat, lon) in coords.items():
            lats.append(lat)
            lons.append(lon)
            if city in depots:
                self.ax.plot(lon, lat, "rs", markersize=8, label="Depot" if "Depot" not in [l.get_label() for l in self.ax.get_lines()] else "")
            else:
                self.ax.plot(lon, lat, "o", color="#89b4fa", markersize=4, alpha=0.6)

        # Vẽ lộ trình
        if routes:
            for idx, route in enumerate(routes):
                color = VEHICLE_COLORS[idx % len(VEHICLE_COLORS)]
                r_lons = []
                r_lats = []
                for city in route:
                    if city in coords:
                        lat, lon = coords[city]
                        r_lons.append(lon)
                        r_lats.append(lat)
                
                if r_lons:
                    self.ax.plot(r_lons, r_lats, "-", color=color, linewidth=1.5, alpha=0.8)
                    # Vẽ mũi tên hướng đi (đơn giản hóa)
                    if len(r_lons) > 1:
                        mid = len(r_lons) // 2
                        self.ax.annotate('', xy=(r_lons[mid], r_lats[mid]), 
                                        xytext=(r_lons[mid-1], r_lats[mid-1]),
                                        arrowprops=dict(arrowstyle='->', color=color, lw=1))

        self.ax.set_aspect('equal', adjustable='datalim')
        self.figure.tight_layout()
        self.canvas.draw()
