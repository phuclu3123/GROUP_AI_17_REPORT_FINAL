"""
VRP-GA Application — Entry Point.

Giải bài toán Vehicle Routing Problem (VRP)
bằng Giải thuật Di truyền (Genetic Algorithm).

Sử dụng:
  - PyQt6       : GUI framework
  - Folium      : Bản đồ tương tác (Leaflet.js)
  - Matplotlib  : Biểu đồ convergence
  - NumPy       : Tính toán

Chạy:  python main.py
"""

import sys
import os

# Thêm thư mục gốc vào sys.path (để import các module)
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Cài đặt font mặc định
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
