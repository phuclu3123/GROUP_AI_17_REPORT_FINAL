# 🧬 VRP — Genetic Algorithm Solver

Ứng dụng desktop giải bài toán **Vehicle Routing Problem (VRP)** bằng **Giải thuật Di truyền (GA)**.

## 📋 Tính năng

- **3 bộ dữ liệu sẵn có**:
  - 15 thành phố Châu Âu
  - 34 tỉnh/thành Việt Nam (sau sáp nhập 2025)
  - 22 Quận/Huyện TP. Hồ Chí Minh

- **Thuật toán GA** (theo slides lý thuyết):
  - Khởi tạo quần thể ngẫu nhiên (Population Initialization)
  - Tournament Selection / Roulette Wheel Selection
  - Order Crossover (OX)
  - Swap Mutation
  - Elitism (giữ cá thể tốt nhất)

- **Giao diện đồ họa PyQt6**:
  - Bản đồ Folium tương tác (Leaflet.js)
  - Biểu đồ convergence (Matplotlib)
  - Panel điều khiển tham số GA
  - Cập nhật real-time mỗi thế hệ

## 🚀 Cài đặt & Chạy

```bash
pip install -r requirements.txt
python main.py
```

## 📁 Cấu trúc dự án

```
VRP_GA_2_APP/
├── main.py                    # Entry point  
├── requirements.txt           # Dependencies
├── data/
│   └── vrp_data.py            # 3 bộ dữ liệu VRP
├── ga_core/
│   ├── chromosome.py          # Biểu diễn nhiễm sắc thể
│   ├── fitness.py             # Hàm đánh giá fitness
│   ├── selection.py           # Tournament / Roulette Selection
│   ├── crossover.py           # Order Crossover (OX)
│   ├── mutation.py            # Swap Mutation
│   └── ga_engine.py           # Vòng lặp GA chính
├── gui/
│   ├── main_window.py         # Cửa sổ chính
│   ├── control_panel.py       # Panel tham số GA
│   ├── map_widget.py          # Bản đồ Folium
│   └── chart_widget.py        # Biểu đồ Matplotlib
└── utils/
    └── constants.py           # Hằng số & màu sắc
```

## 📐 Tham số GA

| Tham số | Mô tả | Mặc định |
|---------|--------|----------|
| n | Kích thước quần thể | 100 |
| r_co | Tỷ lệ crossover | 0.80 |
| r_mu | Tỷ lệ mutation | 0.10 |
| Thế hệ | Số thế hệ tối đa | 300 |
| Tournament k | Kích thước tournament | 5 |
| Số xe | Số lượng xe (vehicles) | 3 |
| Elitism | Số cá thể giữ lại | 2 |
