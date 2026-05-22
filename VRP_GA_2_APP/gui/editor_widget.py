"""
Editor Widget — Bộ công cụ biên tập dữ liệu VRP tương tác.
Bao gồm Sơ đồ hình học, Thanh công cụ và Nhật ký lịch sử.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QListWidget, QLabel, QGroupBox, QButtonGroup
)
from PyQt6.QtCore import pyqtSignal, Qt
from gui.static_map_widget import StaticMapWidget

class EditorWidget(QWidget):
    # Signals để gửi về MainWindow
    point_added = pyqtSignal(float, float, bool) # lat, lon, is_depot
    point_removed_by_name = pyqtSignal(str)
    undo_requested = pyqtSignal()
    clear_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self.mode = "add_customer" # default mode
        self._update_ui_styles()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 1. Toolbar
        toolbar_group = QGroupBox("🛠 Công cụ Biên tập")
        toolbar_layout = QHBoxLayout(toolbar_group)
        
        self.btn_add_customer = QPushButton("📍 Thêm Khách")
        self.btn_add_customer.setCheckable(True)
        self.btn_add_customer.setChecked(True)
        
        self.btn_add_depot = QPushButton("🏠 Thêm Kho")
        self.btn_add_depot.setCheckable(True)
        
        self.btn_delete_mode = QPushButton("🗑 Chế độ Xóa")
        self.btn_delete_mode.setCheckable(True)
        
        # Nhóm các nút mode lại để chỉ chọn 1 lúc
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.btn_add_customer)
        self.mode_group.addButton(self.btn_add_depot)
        self.mode_group.addButton(self.btn_delete_mode)
        
        self.btn_undo = QPushButton("↩️ Hoàn tác")
        self.btn_clear = QPushButton("🧹 Xóa hết")
        self.btn_clear.setStyleSheet("color: #f38ba8;")
        
        toolbar_layout.addWidget(self.btn_add_customer)
        toolbar_layout.addWidget(self.btn_add_depot)
        toolbar_layout.addWidget(self.btn_delete_mode)
        toolbar_layout.addSpacing(20)
        toolbar_layout.addWidget(self.btn_undo)
        toolbar_layout.addWidget(self.btn_clear)
        
        main_layout.addWidget(toolbar_group)
        
        # 2. Main Content (Map + Log)
        content_layout = QHBoxLayout()
        
        # Sơ đồ Matplotlib
        self.map_view = StaticMapWidget()
        content_layout.addWidget(self.map_view, stretch=3)
        
        # Log Lịch sử
        log_group = QGroupBox("📜 Nhật ký Điểm")
        log_layout = QVBoxLayout(log_group)
        self.list_log = QListWidget()
        self.list_log.setStyleSheet("background-color: #181825; color: #cdd6f4; border: none;")
        log_layout.addWidget(self.list_log)
        
        self.lbl_info = QLabel("CHẾ ĐỘ: ĐANG THÊM KHÁCH HÀNG")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_info.setStyleSheet(
            "background-color: #a6e3a1; color: #11111b; font-weight: bold; "
            "padding: 8px; border-radius: 5px; font-size: 13px;"
        )
        log_layout.addWidget(self.lbl_info)
        
        content_layout.addWidget(log_group, stretch=1)
        main_layout.addLayout(content_layout)

    def _connect_signals(self):
        self.map_view.point_added.connect(self._handle_map_click)
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        self.btn_clear.clicked.connect(self.clear_requested.emit)
        
        self.btn_add_customer.clicked.connect(lambda: self._set_mode("add_customer"))
        self.btn_add_depot.clicked.connect(lambda: self._set_mode("add_depot"))
        self.btn_delete_mode.clicked.connect(lambda: self._set_mode("delete"))

    def _set_mode(self, mode):
        self.mode = mode
        self._update_ui_styles()

    def _update_ui_styles(self):
        # Reset styles
        base_style = "padding: 8px; font-weight: bold; border-radius: 4px;"
        self.btn_add_customer.setStyleSheet(base_style + "background-color: #313244; color: #cdd6f4;")
        self.btn_add_depot.setStyleSheet(base_style + "background-color: #313244; color: #cdd6f4;")
        self.btn_delete_mode.setStyleSheet(base_style + "background-color: #313244; color: #cdd6f4;")

        if self.mode == "add_customer":
            self.btn_add_customer.setStyleSheet(base_style + "background-color: #a6e3a1; color: #11111b; border: 2px solid white;")
            self.lbl_info.setText("📍 CHẾ ĐỘ: THÊM KHÁCH HÀNG")
            self.lbl_info.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold; padding: 8px; border-radius: 5px;")
        elif self.mode == "add_depot":
            self.btn_add_depot.setStyleSheet(base_style + "background-color: #89b4fa; color: #11111b; border: 2px solid white;")
            self.lbl_info.setText("🏠 CHẾ ĐỘ: THÊM KHO HÀNG")
            self.lbl_info.setStyleSheet("background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 8px; border-radius: 5px;")
        elif self.mode == "delete":
            self.btn_delete_mode.setStyleSheet(base_style + "background-color: #f38ba8; color: #11111b; border: 2px solid white;")
            self.lbl_info.setText("🗑 CHẾ ĐỘ: XÓA ĐIỂM")
            self.lbl_info.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 8px; border-radius: 5px;")

    def _handle_map_click(self, lat, lon, is_depot_unused):
        # is_depot_unused bỏ qua vì ta dùng mode từ nút bấm
        if self.mode == "add_customer":
            self.point_added.emit(lat, lon, False)
        elif self.mode == "add_depot":
            self.point_added.emit(lat, lon, True)
        elif self.mode == "delete":
            # Ta gửi tọa độ về để MainWindow tìm điểm xóa
            # Reuse signal point_removed from map_view (ta sẽ sửa lại MainWindow connect tới đây)
            self.map_view.point_removed.emit(lat, lon)

    def add_log_entry(self, name, lat, lon, is_depot):
        type_str = "[KHO]" if is_depot else "[KH ]"
        entry = f"{type_str} {name}: ({lat:.2f}, {lon:.2f})"
        self.list_log.insertItem(0, entry) # Thêm vào đầu danh sách

    def remove_log_entry(self, name):
        # Tìm và xóa dòng chứa name
        for i in range(self.list_log.count()):
            if name in self.list_log.item(i).text():
                self.list_log.takeItem(i)
                break

    def clear_log(self):
        self.list_log.clear()

    def update_plot(self, coords, depots, routes=None):
        self.map_view.update_plot(coords, depots, routes)
