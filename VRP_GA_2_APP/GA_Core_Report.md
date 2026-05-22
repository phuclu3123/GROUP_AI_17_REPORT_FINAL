# Báo Cáo Chi Tiết: Module `ga_core` — Giải Thuật Di Truyền (Genetic Algorithm) cho VRP

---

## 1. Tổng Quan

Bài toán **VRP (Vehicle Routing Problem)** thuộc nhóm NP-Hard — tức là không có giải thuật đa thức nào tìm được lời giải tối ưu tuyệt đối trong thời gian hợp lý khi số điểm lớn. **Giải Thuật Di Truyền (Genetic Algorithm — GA)** là một phương pháp **meta-heuristic** lấy cảm hứng từ quá trình tiến hóa tự nhiên (Darwin) để tìm lời giải **gần tối ưu (near-optimal)** trong thời gian chấp nhận được.

Module `ga_core` trong dự án này gồm **7 file Python**, mỗi file đảm nhận một vai trò riêng biệt trong pipeline GA:

```
ga_core/
├── chromosome.py     # Biểu diễn lời giải (cá thể)
├── cost_matrix.py    # Xây dựng ma trận chi phí
├── fitness.py        # Hàm đánh giá chất lượng lời giải
├── selection.py      # Chọn lọc cha mẹ
├── crossover.py      # Lai ghép tạo con cái
├── mutation.py       # Đột biến duy trì đa dạng
├── ga_engine.py      # Vòng lặp GA chính (PyQt6 thread)
└── ga_runner.py      # Runner độc lập (không GUI)
```

---

## 2. Biểu Diễn Lời Giải — `chromosome.py`

### 2.1 Cấu Trúc Chromosome

Trong GA, mỗi **cá thể (individual)** hay **chromosome** đại diện cho **một lời giải hoàn chỉnh** của bài toán VRP.

| Thuộc tính | Kiểu | Ý nghĩa |
|---|---|---|
| `genes` | `List[str]` | Hoán vị các thành phố khách hàng (không gồm depot) |
| `breaks` | `List[int]` | Danh sách chỉ số phân chia `genes` cho từng xe |
| `num_vehicles` | `int` | Số lượng xe tham gia phân phối |
| `fitness` | `float` | Giá trị fitness = `1 / total_cost` |
| `total_cost` | `float` | Tổng chi phí của lời giải |
| `conflicts` | `int` | Số lần vi phạm ràng buộc (tải trọng, thời gian) |

### 2.2 Cách Mã Hóa (Encoding)

Cách mã hóa sử dụng là **Permutation Encoding + Break Points**:

```
genes  = [A, B, C, D, E, F]
breaks = [2, 4]
→ Xe 1: Depot → A → B → Depot
→ Xe 2: Depot → C → D → Depot
→ Xe 3: Depot → E → F → Depot
```

> **Ký hiệu:** `breaks = [b₁, b₂, ..., b_{k-1}]` với `k` = số xe.
> Mỗi `bᵢ` là chỉ số trong mảng `genes` đánh dấu điểm cắt giữa 2 xe liên tiếp.

**Ưu điểm của cách mã hóa này:**
- Không cần gene đặc biệt đại diện cho "trở về depot"
- Tránh lời giải không hợp lệ (mỗi thành phố xuất hiện đúng 1 lần)
- Cho phép tiến hóa **cả thứ tự thành phố lẫn phân bổ xe** một cách độc lập

### 2.3 Khởi Tạo Break Points Ngẫu Nhiên

```python
@staticmethod
def _init_breaks(n: int, num_vehicles: int) -> List[int]:
    candidates = random.sample(range(1, n), min(num_vehicles - 1, n - 1))
    return sorted(candidates)
```

> **Tại sao dùng ngẫu nhiên thay vì chia đều?**
> Nếu chia đều, mọi cá thể ban đầu có cùng cấu trúc phân bổ xe → quần thể **thiếu đa dạng** → hội tụ sớm (premature convergence).

### 2.4 Chọn Depot Tối Ưu

Khi có nhiều depot (MDVRP), mỗi đoạn route sẽ được gán về depot gần nhất theo **tổng chi phí vòng tròn**:

$$\text{cost}(depot_d, \text{segment}) = D[d][f] + D[l][d]$$

Trong đó:
- $D[d][f]$ = khoảng cách từ depot $d$ đến thành phố **đầu tiên** $f$ của đoạn
- $D[l][d]$ = khoảng cách từ thành phố **cuối cùng** $l$ về depot $d$

```python
round_trip_cost = cost_matrix[d_idx, f_idx] + cost_matrix[l_idx, d_idx]
```

---

## 3. Ma Trận Chi Phí — `cost_matrix.py`

### 3.1 Cấu Trúc

Thay vì dùng `Dict[str, Dict[str, float]]` (tra cứu O(1) nhưng cache miss cao), module sử dụng **numpy ndarray** `[N × N]`:

$$C \in \mathbb{R}^{N \times N}, \quad C_{ij} = \text{chi phí từ thành phố } i \text{ đến thành phố } j$$

```python
city_index = {"Depot": 0, "A": 1, "B": 2, ...}
cost = cost_matrix[city_index["A"], city_index["B"]]  # O(1), cache-friendly
```

### 3.2 Công Thức Haversine

Khoảng cách thực tế giữa 2 điểm GPS $(\phi_1, \lambda_1)$ và $(\phi_2, \lambda_2)$:

$$a = \sin^2\!\left(\frac{\Delta\phi}{2}\right) + \cos\phi_1 \cdot \cos\phi_2 \cdot \sin^2\!\left(\frac{\Delta\lambda}{2}\right)$$

$$d = 2R \cdot \arcsin(\sqrt{a}), \quad R = 6371 \text{ km}$$

```python
a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
cost_matrix = R * c
```

---

## 4. Hàm Đánh Giá — `fitness.py`

### 4.1 Công Thức Tổng Chi Phí

$$\text{TotalCost} = \underbrace{\sum_{\text{routes}} \sum_{i \to j} D_{ij}}_{\text{Chi phí di chuyển}} + \underbrace{\sum_{c \notin \text{Depot}} \text{fee}(c)}_{\text{Phí bốc xếp}} + \underbrace{P_{\text{capacity}}}_{\text{Phạt tải trọng}} + \underbrace{P_{\text{time}}}_{\text{Phạt thời gian}}$$

### 4.2 Phạt Tải Trọng (CVRP)

$$P_{\text{capacity}} = 10{,}000 \times \max(0,\ \text{route\_demand} - Q)$$

Trong đó $Q$ = sức chứa tối đa (`max_capacity`). Hệ số phạt `10,000` đảm bảo lời giải vi phạm tải trọng luôn tệ hơn bất kỳ lời giải hợp lệ nào.

### 4.3 Phạt Thời Gian — Soft Time Window (VRPTW)

Mỗi khách hàng $c$ có cửa sổ thời gian $[e_c, l_c]$ (earliest, latest). Quy tắc:

| Trường hợp | Hành động |
|---|---|
| Đến sớm ($t < e_c$) | **Chờ** đến $e_c$, không phạt |
| Đến đúng giờ ($e_c \le t \le l_c$) | Không phạt |
| Đến muộn ($t > l_c$) | Phạt tuyến tính: $100 \times (t - l_c)$ |

```python
if current_time > due:
    total_cost += (current_time - due) * 100.0
    total_conflicts += 1
```

Tốc độ xe: $v = \frac{40 \text{ km/h}}{60} = \frac{2}{3}$ km/phút.

### 4.4 Hàm Fitness

$$\text{Fitness}(h) = \frac{1}{\text{TotalCost}(h)}$$

> **Ý nghĩa:** Lời giải có chi phí càng **thấp** thì fitness càng **cao**. Giá trị fitness luôn dương và nằm trong $(0, 1]$ (khi `TotalCost ≥ 1`).

---

## 5. Chọn Lọc — `selection.py`

### 5.1 Tournament Selection (Phương pháp chính)

**Quy trình:**
1. Chọn ngẫu nhiên $k$ cá thể từ quần thể (không hoàn lại)
2. Trả về cá thể có fitness **cao nhất** trong nhóm $k$

$$\text{winner} = \arg\max_{h \in \text{tournament}} \text{Fitness}(h)$$

```python
candidates = random.sample(population, k)
winner = max(candidates, key=lambda c: c.fitness)
```

**Tham số:** `tournament_size = 5` (mặc định).

> **Tại sao dùng Tournament thay vì Roulette Wheel?**
> Hàm phạt tải trọng `10,000 × overflow` tạo ra chênh lệch fitness **hàng nghìn lần** giữa lời giải hợp lệ và không hợp lệ. Với Roulette Wheel, cá thể hợp lệ sẽ chiếm gần 100% xác suất → quần thể mất đa dạng ngay từ thế hệ đầu. Tournament chỉ so sánh **tương đối** nên tránh được vấn đề này.

### 5.2 Roulette Wheel Selection (Tham khảo)

$$P(\text{chọn } h_i) = \frac{\text{Fitness}(h_i)}{\sum_{j=1}^{N} \text{Fitness}(h_j)}$$

```python
pick = random.uniform(0, total_fitness)
# Duyệt tích lũy đến khi vượt pick
```

---

## 6. Lai Ghép — `crossover.py`

### 6.1 Order Crossover (OX)

OX là toán tử lai ghép chuẩn cho bài toán **permutation** (hoán vị), đảm bảo con cái là một hoán vị hợp lệ (không trùng lặp thành phố).

**Quy trình OX:**

```
Parent1: [A B | C D E | F G]
Parent2: [C F | E A G | D B]
          ←  segment [2,5) từ P1  →

Child1:
  Bước 1: Giữ segment: [_ _ C D E _ _]
  Bước 2: Lấy P2 theo thứ tự, bỏ {C,D,E}: [F, A, G, B]
  Bước 3: Điền vào vị trí còn trống:      [F A C D E G B]
```

```python
start, end = sorted(random.sample(range(size), 2))
child1_genes = _ox_build(parent1.genes, parent2.genes, start, end)
```

### 6.2 Kế Thừa Break Points

> **Cải tiến then chốt:** Con cái kế thừa `breaks` từ bố/mẹ tương ứng, **không reset về chia đều**.

```python
c1 = Chromosome(child1_genes, parent1.num_vehicles, breaks=list(parent1.breaks))
c2 = Chromosome(child2_genes, parent2.num_vehicles, breaks=list(parent2.breaks))
```

Điều này cho phép thuật toán tiến hóa **đồng thời**:
- Thứ tự thăm các thành phố (qua OX)
- Cách phân bổ khách hàng giữa các xe (qua kế thừa breaks)

---

## 7. Đột Biến — `mutation.py`

### 7.1 Swap Mutation

Hoán đổi ngẫu nhiên 2 thành phố trong `genes`:

```
Trước: [A B C D E F]
Sau:   [A D C B E F]   (hoán vị B ↔ D)
```

### 7.2 Insertion Mutation

Lấy 1 thành phố ra và chèn vào vị trí khác:

```
Trước: [A B C D E F]
Lấy B (i=1), chèn vào j=4:
Sau:   [A C D E B F]
```

> Thường hiệu quả hơn Swap cho bài toán routing vì thay đổi **liên tục** trong route thay vì **rời rạc**.

### 7.3 Break Point Mutation (Đặc trưng của VRP)

Dịch chuyển một break point ngẫu nhiên **±1 vị trí**:

```
breaks = [2, 4]  (Xe1: [0,2), Xe2: [2,4), Xe3: [4,6))
Dịch breaks[0]: 2 → 3
breaks = [3, 4]  (Xe1: [0,3), Xe2: [3,4), Xe3: [4,6))
→ Xe 1 nhận thêm 1 khách hàng từ Xe 2
```

```python
def mutate_breaks(self, n: int) -> None:
    idx = random.randrange(len(self.breaks))
    delta = random.choice([-1, 1])
    new_val = self.breaks[idx] + delta
    if lower < new_val < upper:
        self.breaks[idx] = new_val
```

> **Lưu ý quan trọng:** Nếu không có Break Mutation, thuật toán chỉ tối ưu **thứ tự thành phố** mà **không bao giờ** tối ưu được cách phân bổ giữa các xe.

### 7.4 Phân Bổ Đột Biến Trong Quần Thể

```python
# Gene mutation: mutation_rate × N cá thể
num_mutants = int(mutation_rate * N)   # VD: 5% × 100 = 5

# Break mutation: break_mutation_rate × N cá thể (độc lập)
num_break_mutants = int(break_mutation_rate * N)  # VD: 10% × 100 = 10
```

Hai loại đột biến hoạt động **độc lập** — một cá thể có thể bị cả hai loại.

---

## 8. Vòng Lặp Tiến Hóa — `ga_engine.py` & `ga_runner.py`

### 8.1 Pseudocode Tổng Quát

```
1. Khởi tạo quần thể P₀ kích thước N (ngẫu nhiên)
2. Đánh giá fitness toàn bộ P₀
3. best ← cá thể tốt nhất trong P₀
4. Lặp (gen = 1 → G):
   a. Elitism: lưu k cá thể tốt nhất (elites)
   b. Selection: chọn N cha mẹ bằng Tournament
   c. Crossover: tạo offspring từ cha mẹ (tỉ lệ p_c)
   d. Reproduction: giữ lại (1-p_c)×N cá thể không qua crossover
   e. Ghép: P_new = elites ∪ offspring ∪ reproduced (cắt về N)
   f. Mutation: đột biến gene + break của P_new (trừ elites)
   g. Evaluate: chỉ tính fitness cá thể chưa có cost
   h. Cập nhật best nếu cải thiện
   i. Kiểm tra Early Stopping
5. Trả về best và lịch sử hội tụ
```

### 8.2 Elitism

Giữ lại $k$ cá thể tốt nhất mỗi thế hệ, **không qua mutation**:

```python
elites = [population[i].copy() for i in range(k)]
# ...
next_gen = elites + offspring + reproduced
non_elite = next_gen[k:]
non_elite = mutate_population(non_elite, ...)  # Chỉ mutate non-elite
```

> **Ý nghĩa:** Đảm bảo lời giải tốt nhất **không bao giờ bị mất** qua các thế hệ (monotone non-increasing best cost).

### 8.3 Early Stopping

```python
if gen_best.total_cost < best.total_cost:
    best = gen_best.copy()
    no_improve_count = 0
else:
    no_improve_count += 1

if no_improve_count >= patience:
    break  # Dừng sớm
```

| Tham số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `patience` | 50 | Dừng nếu không cải thiện sau 50 thế hệ liên tiếp |
| `generations` | 300–500 | Số thế hệ tối đa |

### 8.4 Đánh Giá Thông Minh (Lazy Evaluation)

```python
unevaluated = [c for c in next_gen if c.total_cost == float("inf")]
evaluate_population(unevaluated, ...)
```

Chỉ tính fitness cho cá thể **chưa được đánh giá** (elites đã có cost từ thế hệ trước) → tiết kiệm ~$k/N$ lần tính fitness mỗi thế hệ.

---

## 9. Cấu Hình Tham Số — `GAConfig`

| Tham số | Ký hiệu | Giá trị mặc định | Ảnh hưởng |
|---|---|---|---|
| `pop_size` | $N$ | 100 | Kích thước quần thể |
| `num_generations` | $G$ | 500 | Số thế hệ tối đa |
| `crossover_rate` | $p_c$ | 0.8 | Tỉ lệ lai ghép |
| `mutation_rate` | $p_m$ | 0.05–0.2 | Tỉ lệ đột biến gene |
| `break_mutation_rate` | $p_{bm}$ | 0.1–0.3 | Tỉ lệ đột biến break |
| `tournament_size` | $k$ | 5 | Áp lực chọn lọc |
| `elitism_count` | $e$ | 2–5 | Số cá thể ưu tú giữ lại |
| `patience` | $p$ | 50 | Ngưỡng early stopping |

> **Ghi chú điều chỉnh tham số:**
> - `tournament_size` lớn → chọn lọc **áp lực cao** → hội tụ nhanh nhưng dễ bẫy cực trị địa phương
> - `mutation_rate` cao → khám phá nhiều hơn → hội tụ chậm hơn
> - `elitism_count` quá lớn → mất đa dạng → hội tụ sớm

---

## 10. Kiến Trúc Đa Luồng — PyQt6

```
Main Thread (GUI)
    │
    ├── GAWorker (QThread)
    │       │
    │       └── GAEngine.run()
    │               │
    │               ├── generation_done.emit(gen, fitness, cost, conflicts, routes)
    │               │         ↓ (signal/slot — thread-safe)
    │               │   GUI cập nhật biểu đồ hội tụ + bản đồ
    │               │
    │               └── finished.emit(final_routes)
    │
    └── [Stop Button] → GAWorker.stop() → engine._stop_flag = True
```

- `GAEngine` kế thừa `QObject` để dùng signal/slot của Qt
- `GAWorker` là `QThread` wrapper, forward signal từ engine về GUI
- `time.sleep(0.001)` mỗi thế hệ để nhường CPU cho GUI thread

---

## 11. Sơ Đồ Luồng Dữ Liệu

```
Input Data
  (cities, depots, coords, demands, fees, capacity, time_windows)
        │
        ▼
cost_matrix.py ──→ numpy ndarray [N×N] + city_index dict
        │
        ▼
chromosome.py  ──→ Quần thể ban đầu P₀ (N cá thể, genes ngẫu nhiên)
        │
        ▼
fitness.py     ──→ TotalCost + Fitness cho mỗi cá thể
        │
        ▼
 ┌──────────────────────────────────────┐
 │  VÒNG LẶP TIẾN HÓA (ga_engine.py)   │
 │                                      │
 │  selection.py → Tournament           │
 │  crossover.py → OX + kế thừa breaks │
 │  mutation.py  → Swap/Insert + Break  │
 │  fitness.py   → Lazy evaluation      │
 └──────────────────────────────────────┘
        │
        ▼
GAResult: best_chromosome, best_cost, history[]
```

---

## 12. Phân Tích Độ Phức Tạp

| Bước | Độ phức tạp | Ghi chú |
|---|---|---|
| Khởi tạo quần thể | $O(N \cdot n)$ | $N$ = pop_size, $n$ = số thành phố |
| Đánh giá 1 cá thể | $O(n)$ | Duyệt từng cặp trong route |
| Đánh giá quần thể | $O(N \cdot n)$ | Song song hóa được |
| Tournament Selection | $O(k)$ | $k$ = tournament_size |
| OX Crossover | $O(n)$ | Build child genes |
| Toàn bộ 1 thế hệ | $O(N \cdot n)$ | Bottleneck là evaluate |
| Toàn bộ GA | $O(G \cdot N \cdot n)$ | $G$ = số thế hệ |

Với $G=300, N=100, n=20$: $\approx 600{,}000$ phép tính cơ bản — **rất nhanh** nhờ numpy.

---

## 13. Ví Dụ Minh Họa

### Bài toán ví dụ

- 6 khách hàng: `{A, B, C, D, E, F}`, 1 depot: `{Depot}`
- 2 xe, sức chứa mỗi xe: $Q = 30$
- Nhu cầu: `A=10, B=8, C=12, D=5, E=9, F=7`

### Chromosome ban đầu (ngẫu nhiên)

```
genes  = [C, A, E, B, D, F]
breaks = [3]           → Xe 1: [C,A,E], Xe 2: [B,D,F]
```

Kiểm tra tải trọng:
- Xe 1: `12+10+9 = 31 > 30` → **Vi phạm** → Phạt `10,000 × 1 = 10,000`
- Xe 2: `8+5+7 = 20 ≤ 30` → Hợp lệ

### Sau vài thế hệ tiến hóa

```
genes  = [A, B, E, F, C, D]
breaks = [4]           → Xe 1: [A,B,E,F] demand=34 → vẫn vi phạm
```

Break mutation dịch `breaks[0]`: 4 → 3:
```
breaks = [3]           → Xe 1: [A,B,E] demand=27 ✓, Xe 2: [F,C,D] demand=24 ✓
```

→ **Vi phạm được giải quyết nhờ Break Mutation!**

---

## 14. Biến Thể VRP Được Hỗ Trợ

| Biến thể | Ký hiệu | Hỗ trợ | Cơ chế |
|---|---|---|---|
| VRP cơ bản | VRP | ✅ | genes + breaks |
| VRP có tải trọng | CVRP | ✅ | Capacity penalty |
| VRP nhiều depot | MDVRP | ✅ | Chọn depot tối ưu |
| VRP cửa sổ thời gian | VRPTW | ✅ | Soft TW penalty |

---

## 15. Tham Khảo

1. Holland, J.H. (1975). *Adaptation in Natural and Artificial Systems*. MIT Press.
2. Davis, L. (1985). *Applying Adaptive Algorithms to Epistatic Domains*. IJCAI. (Order Crossover — OX)
3. Toth, P. & Vigo, D. (2002). *The Vehicle Routing Problem*. SIAM.
4. Goldberg, D.E. (1989). *Genetic Algorithms in Search, Optimization, and Machine Learning*. Addison-Wesley.

---

*Báo cáo được tổng hợp từ source code `ga_core/` — Dự án VRP-GA, 2026.*
