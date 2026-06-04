# Documentație CoppeliaSim Sim — Pioneer P3-DX + A*

Acest document descrie integral componenta de simulare robotică din `coppeliasim-sim/`: un robot **Pioneer P3-DX** care navighează autonom într-un mediu cu obstacole, folosind algoritmul **A\*** pentru planificare și un controller proporțional pentru urmărirea drumului.

---

## 1. Privire de ansamblu

Componenta integrează trei lumi diferite:
- **Algoritmică** — A\* pe grid 2D pentru găsirea celui mai scurt drum.
- **Robotică** — model diferențial Pioneer P3-DX, control proporțional pentru urmărire waypoints.
- **Simulare** — CoppeliaSim ca mediu fizic 3D, comunicare prin ZMQ Remote API.

**Funcționalități principale:**
- Discretizare a mediului fizic într-un `GridMap` (rânduri × coloane, celule pătrate).
- Algoritm **A\*** cu euristică Euclidiană, 8-vecinătate, anti-corner-cutting.
- **Path smoothing** cu line-of-sight Bresenham (string-pulling) — elimină zig-zag-ul.
- **Obstacle inflation** — buffer de siguranță în jurul obstacolelor pentru raza robotului.
- Wrapper Python peste CoppeliaSim ZMQ Remote API pentru controlul robotului.
- Controller proporțional (P) cu factor de aliniere pentru urmărirea drumului.
- Tot proiectul e configurabil din CLI (`--goal`, `--map`, `--inflate`, `--no-smooth`).

---

## 2. Structura proiectului

```
coppeliasim-sim/
├── src/
│   ├── main.py                      # Entry point CLI
│   ├── world/
│   │   └── grid_map.py              # GridMap + GridCell (discretizare 2D)
│   ├── algorithms/
│   │   └── astar.py                 # AStarPathfinder + smooth_path
│   └── controller/
│       ├── pioneer.py               # Wrapper ZMQ Pioneer P3-DX
│       └── path_executor.py         # Control P pentru waypoints
├── scenes/
│   ├── map.json                     # Harta 20×20 cu obstacole
│   └── README.md                    # Cum se construiește scena .ttt
└── tests/
    └── test_astar.py                # Teste unitare A*
```

---

## 3. Pipeline complet

Fluxul de date de la harta logică la mișcarea fizică a robotului:

```
┌─────────────────┐
│   GridMap       │  rows × cols, cell_size, origin
│ (occupancy)     │  Obstacle inflation cu raza robot
└────────┬────────┘
         │  GridCell (row, col)
         ▼
┌─────────────────┐
│ AStarPathfinder │  find_path(start, goal) → list[GridCell]
│ + smooth_path() │  Reduce zig-zag-ul pe diagonale
└────────┬────────┘
         │  waypoints world (x, y) — metri
         ▼
┌─────────────────┐
│   PathExecutor  │  Control P pe (heading_error, distance_error)
│   (Kp_lin/ang)  │  Reduce viteza liniară când nu e aliniat
└────────┬────────┘
         │  v_linear, v_angular
         ▼
┌─────────────────┐
│   Pioneer       │  Diferențială: (v, ω) → (v_left, v_right)
│   Controller    │  ZMQ Remote API → CoppeliaSim
└─────────────────┘
```

---

## 4. Modelul lumii — `GridMap`

[src/world/grid_map.py](coppeliasim-sim/src/world/grid_map.py)

### 4.1 Discretizarea spațiului

Mediul fizic (în metri) e discretizat într-o grilă 2D de celule pătrate. Convenții:

- Coordonate **world** (CoppeliaSim): metri, axe X/Y.
- Coordonate **grid**: indici `(row, col)`, cu `(0,0)` în colțul stânga-jos.
- Fiecare celulă reprezintă un pătrat de `cell_size` × `cell_size` metri.
- Ocuparea: `True` = obstacol, `False` = liber.

### 4.2 GridCell — coordonate de celulă

[src/world/grid_map.py:21-29](coppeliasim-sim/src/world/grid_map.py#L21-L29):
```python
@dataclass(frozen=True, slots=True)
class GridCell:
    row: int
    col: int

    def __iter__(self):
        yield self.row
        yield self.col
```

Frozen + slots → hashable și ușor, ideal pentru chei de dict în A\*.

### 4.3 Conversia world ↔ grid

Două funcții simetrice care fac conversia între lumea fizică și grila logică.

[src/world/grid_map.py:87-97](coppeliasim-sim/src/world/grid_map.py#L87-L97):
```python
def world_to_grid(self, x: float, y: float) -> GridCell:
    col = int((x - self.origin[0]) / self.cell_size)
    row = int((y - self.origin[1]) / self.cell_size)
    return GridCell(row=row, col=col)

def grid_to_world(self, cell: GridCell) -> tuple[float, float]:
    x = self.origin[0] + (cell.col + 0.5) * self.cell_size
    y = self.origin[1] + (cell.row + 0.5) * self.cell_size
    return (x, y)
```

`grid_to_world` returnează **centrul** celulei (offset `+0.5`), așa că robotul urmărește puncte stabile, nu colțuri.

### 4.4 Vecinătatea cu anti-corner-cutting

A\* folosește 8-vecinătate (sus, jos, stânga, dreapta + 4 diagonale). Pentru mișcările diagonale verificăm că **ambele celule adiacente** sunt libere — altfel robotul ar "tăia colțul" printr-un obstacol.

[src/world/grid_map.py:99-119](coppeliasim-sim/src/world/grid_map.py#L99-L119):
```python
def neighbors(self, cell: GridCell, diagonal: bool = True) -> Iterable[GridCell]:
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonal:
        offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    for dr, dc in offsets:
        n = GridCell(cell.row + dr, cell.col + dc)
        if not self.is_free(n):
            continue
        if abs(dr) + abs(dc) == 2:           # mișcare diagonală
            if (
                not self.is_free(GridCell(cell.row + dr, cell.col))
                or not self.is_free(GridCell(cell.row, cell.col + dc))
            ):
                continue                      # taie colțul → respins
        yield n
```

### 4.5 Inflație obstacole — buffer de siguranță

Robotul Pioneer are diametru ~40 cm. Pe o grilă cu `cell_size=0.25 m`, asta înseamnă că o celulă "liberă" lângă un obstacol poate fi de fapt prea îngustă. Soluția: **dilatăm** obstacolele cu raza robotului (în celule), folosind `scipy.ndimage.binary_dilation`:

[src/world/grid_map.py:121-133](coppeliasim-sim/src/world/grid_map.py#L121-L133):
```python
def inflate_obstacles(self, radius_cells: int) -> None:
    if radius_cells <= 0:
        return
    from scipy.ndimage import binary_dilation

    structure = np.ones((2 * radius_cells + 1, 2 * radius_cells + 1), dtype=bool)
    self._occupancy = binary_dilation(self._occupancy, structure=structure)
```

Astfel A\* va găsi automat drumuri care păstrează robotul departe de pereți, fără să cunoască explicit dimensiunile fizice.

---

## 5. Algoritmul A\*

[src/algorithms/astar.py](coppeliasim-sim/src/algorithms/astar.py)

### 5.1 Formula de evaluare

```
f(n) = g(n) + h(n)
```

| | Semnificație | Implementare |
|---|---|---|
| `g(n)` | costul real de la start la n | 1.0 ortogonal, √2 ≈ 1.414 diagonal |
| `h(n)` | estimare optimistă de la n la goal | distanța Euclidiană |
| `f(n)` | cost total estimat | prioritate în heap |

**Distanța Euclidiană** ca euristică e cheia: robotul Pioneer se poate roti liber, deci se poate deplasa și pe diagonale → o linie dreaptă este întotdeauna ≤ orice drum real → euristica **nu supraestimează** costul (este admisibilă) → A\* este garantat optim.

(Dacă am fi folosit Manhattan, am fi supraestimat costul real pe diagonale și soluția găsită de A\* nu ar mai fi optimă.)

### 5.2 Heap-ul cu tie-breaking

Heapq din Python sortează tupluri, dar la egalitate compară elementul următor. Dacă două celule au același `f`, ar încerca să compare obiectele `GridCell`, ceea ce ar putea fi nedeterminist. Soluția: wrapper care folosește un contor monoton ca tie-breaker:

[src/algorithms/astar.py:33-38](coppeliasim-sim/src/algorithms/astar.py#L33-L38):
```python
@dataclass(order=True)
class _PriorityNode:
    priority: float
    counter: int
    cell: GridCell = field(compare=False)
```

`compare=False` pe `cell` → comparațiile heapului nu ajung niciodată la GridCell.

### 5.3 Bucla principală A\*

[src/algorithms/astar.py:81-107](coppeliasim-sim/src/algorithms/astar.py#L81-L107):
```python
while open_heap:
    node = heapq.heappop(open_heap)
    current = node.cell

    if current in closed:
        continue
    if current == goal:
        return self._reconstruct(came_from, current)

    in_open.discard(current)
    closed.add(current)

    for neighbor in gm.neighbors(current, diagonal=allow_diagonal):
        if neighbor in closed:
            continue
        step_cost = self._step_cost(current, neighbor)
        tentative_g = g_score[current] + step_cost

        if tentative_g < g_score.get(neighbor, float("inf")):
            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            f = tentative_g + self._heuristic(neighbor, goal)
            counter += 1
            heapq.heappush(open_heap, _PriorityNode(f, counter, neighbor))
            in_open.add(neighbor)
```

Pattern clasic A\*:
- `g_score[neighbor]` se actualizează doar dacă noul `g` e mai mic decât cel precedent (relaxare).
- `came_from` păstrează părintele fiecărei celule pentru reconstrucția drumului.
- `closed` previne re-procesarea unei celule deja finalizate.
- La extragere din heap, dacă celula e deja în `closed` (variantă mai veche), o sărim — alternativă la "decrease key" pe care heapq nu o suportă direct.

### 5.4 Reconstrucția drumului

Mergi înapoi din `goal` pe pointerii `came_from` până la start, apoi inversezi.

[src/algorithms/astar.py:130-137](coppeliasim-sim/src/algorithms/astar.py#L130-L137):
```python
@staticmethod
def _reconstruct(came_from, end) -> list[GridCell]:
    path = [end]
    while end in came_from:
        end = came_from[end]
        path.append(end)
    path.reverse()
    return path
```

### 5.5 Path smoothing — string-pulling

A\* pe grid produce drumuri cu pași discreți (0.25 m) și mișcări la 45°. Pentru un robot fizic e ineficient. **String-pulling** elimină waypoints intermediare dacă există line-of-sight direct între ele:

[src/algorithms/astar.py:139-156](coppeliasim-sim/src/algorithms/astar.py#L139-L156):
```python
@staticmethod
def smooth_path(path: list[GridCell], grid_map: GridMap) -> list[GridCell]:
    if len(path) <= 2:
        return path
    smoothed = [path[0]]
    anchor = 0
    for i in range(2, len(path)):
        if not AStarPathfinder._has_line_of_sight(path[anchor], path[i], grid_map):
            smoothed.append(path[i - 1])
            anchor = i - 1
    smoothed.append(path[-1])
    return smoothed
```

Ținem un "ancor" (ultimul waypoint păstrat). Avansăm `i` cât timp există line-of-sight direct ancor→i. Când line-of-sight se rupe, păstrăm `i-1` ca nou ancor.

### 5.6 Line-of-sight Bresenham

Linia dreaptă între două celule de grid se discretizează cu algoritmul Bresenham — același folosit la rasterizarea liniilor în grafică:

[src/algorithms/astar.py:158-180](coppeliasim-sim/src/algorithms/astar.py#L158-L180):
```python
@staticmethod
def _has_line_of_sight(a: GridCell, b: GridCell, grid_map: GridMap) -> bool:
    r0, c0 = a.row, a.col
    r1, c1 = b.row, b.col
    dr = abs(r1 - r0)
    dc = abs(c1 - c0)
    sr = 1 if r0 < r1 else -1
    sc = 1 if c0 < c1 else -1
    err = dr - dc

    while True:
        if not grid_map.is_free(GridCell(r0, c0)):
            return False
        if r0 == r1 and c0 == c1:
            return True
        e2 = 2 * err
        if e2 > -dc:
            err -= dc
            r0 += sr
        if e2 < dr:
            err += dr
            c0 += sc
```

Verificăm toate celulele intersectate de linie. Dacă măcar una e obstacol, line-of-sight rupt.

---

## 6. Controlul fizic — Pioneer P3-DX

### 6.1 Modelul diferențial

[src/controller/pioneer.py](coppeliasim-sim/src/controller/pioneer.py)

Pioneer P3-DX are **tracțiune diferențială**: două roți motrice independente (stânga, dreapta) + o roată cu rolă liberă. Translația și rotația apar din diferența și suma vitezelor roților:

```
v_linear  = (v_left + v_right) · R / 2          [m/s]
v_angular = (v_right - v_left) · R / L          [rad/s]
```

unde `R` = raza roții, `L` = distanța dintre roți.

**Conversia inversă** (din comenzi de înalt nivel către roți):

[src/controller/pioneer.py:103-115](coppeliasim-sim/src/controller/pioneer.py#L103-L115):
```python
def set_velocity(self, linear: float, angular: float) -> None:
    R = self.spec.wheel_radius
    L = self.spec.wheel_base
    v_left = (linear - angular * L / 2.0) / R
    v_right = (linear + angular * L / 2.0) / R
    self.set_wheel_velocities(v_left, v_right)
```

Parametrii fizici Pioneer P3-DX:

[src/controller/pioneer.py:26-31](coppeliasim-sim/src/controller/pioneer.py#L26-L31):
```python
@dataclass
class PioneerSpec:
    wheel_radius: float = 0.0975        # m
    wheel_base: float = 0.381           # m
    max_wheel_speed: float = 2.0        # rad/s
```

### 6.2 Comunicarea ZMQ Remote API

[src/controller/pioneer.py:66-72](coppeliasim-sim/src/controller/pioneer.py#L66-L72):
```python
def connect(self) -> None:
    self._client = RemoteAPIClient(self.host, self.port)
    self._sim = self._client.require("sim")
    self._left_handle = self._sim.getObject(self.LEFT_MOTOR)
    self._right_handle = self._sim.getObject(self.RIGHT_MOTOR)
    self._robot_handle = self._sim.getObject(self.ROBOT_HANDLE)
```

CoppeliaSim expune un server ZMQ pe portul 23000 (implicit). Clientul Python obține handle-uri pentru obiectele scenei (motoarele, robotul în sine), apoi le folosește pentru a citi poziția și a seta viteze.

**Mod stepping** — controlul mai precis: în loc să lăsăm CoppeliaSim să ruleze liber, avansăm simularea pas cu pas, comandat din Python:

[src/controller/pioneer.py:81-93](coppeliasim-sim/src/controller/pioneer.py#L81-L93):
```python
def start_simulation(self) -> None:
    self._ensure_connected()
    self._sim.setStepping(True)
    self._sim.startSimulation()

def step(self) -> None:
    """Avansează simularea cu un pas (mod stepping)."""
    self._sim.step()
```

### 6.3 Citirea poziției robotului

[src/controller/pioneer.py:120-125](coppeliasim-sim/src/controller/pioneer.py#L120-L125):
```python
def get_pose(self) -> tuple[float, float, float]:
    pos = self._sim.getObjectPosition(self._robot_handle, -1)
    ori = self._sim.getObjectOrientation(self._robot_handle, -1)
    return float(pos[0]), float(pos[1]), float(ori[2])
```

Returnează `(x, y, θ)` — poziție în plan și orientare yaw în radiani.

### 6.4 Normalizarea unghiurilor

Diferențe de unghi care depășesc `±π` trebuie aduse în intervalul `[-π, π]` pentru control proporțional corect:

[src/controller/pioneer.py:131-134](coppeliasim-sim/src/controller/pioneer.py#L131-L134):
```python
@staticmethod
def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))
```

Trucul `atan2(sin, cos)` e o expresie idiomatică — exploatează periodicitatea sin/cos ca să normalizeze fără modulo manual.

---

## 7. Urmărirea waypoints — `PathExecutor`

[src/controller/path_executor.py](coppeliasim-sim/src/controller/path_executor.py)

### 7.1 Strategia de control

Pentru fiecare waypoint țintă:
1. Calculează **distance_error** (cât a mai rămas) și **heading_error** (cu cât trebuie rotit).
2. Comenzi de viteză:
   - `v_angular = Kp_angular · heading_error` (rotește spre țintă).
   - `v_linear = Kp_linear · distance · cos(heading_error)` — **avansează doar când e aliniat**.
3. Treci la următorul waypoint când `distance < waypoint_tolerance`.

### 7.2 Configurarea controlerului

[src/controller/path_executor.py:27-38](coppeliasim-sim/src/controller/path_executor.py#L27-L38):
```python
@dataclass
class ExecutorConfig:
    waypoint_tolerance: float = 0.12          # m
    final_tolerance: float = 0.10              # m
    kp_linear: float = 0.8
    kp_angular: float = 2.5
    max_linear: float = 0.4                    # m/s
    max_angular: float = 1.5                   # rad/s
    align_threshold_rad: float = math.radians(30)
    control_dt: float = 0.05                   # s
    timeout_seconds: float = 60.0
```

| Parametru | Rol |
|-----------|-----|
| `kp_linear` | Câștig pentru distanță. Mai mare = mai rapid, dar oscilează. |
| `kp_angular` | Câștig pentru orientare. Robotul trebuie să se alinieze rapid. |
| `align_threshold_rad` | Sub acest unghi robotul accelerează liniar; peste, doar rotește. |
| `waypoint_tolerance` | Distanță până la waypoint pentru a trece la următorul. |
| `final_tolerance` | Toleranță mai strictă pentru ținta finală (10 cm vs 12 cm intermediar). |

### 7.3 Bucla de control

[src/controller/path_executor.py:65-93](coppeliasim-sim/src/controller/path_executor.py#L65-L93):
```python
while True:
    if (time.perf_counter() - start_time) > cfg.timeout_seconds:
        self.controller.stop()
        return False

    x, y, theta = self.controller.get_pose()
    dx = wx - x
    dy = wy - y
    distance = math.hypot(dx, dy)

    if distance < tolerance:
        break

    target_angle = math.atan2(dy, dx)
    heading_error = self.controller.normalize_angle(target_angle - theta)

    v_angular = cfg.kp_angular * heading_error
    alignment_factor = max(0.0, math.cos(heading_error))
    if abs(heading_error) > cfg.align_threshold_rad:
        v_linear = 0.0
    else:
        v_linear = cfg.kp_linear * distance * alignment_factor

    v_linear = max(-cfg.max_linear, min(cfg.max_linear, v_linear))
    v_angular = max(-cfg.max_angular, min(cfg.max_angular, v_angular))

    self.controller.set_velocity(v_linear, v_angular)
    self.controller.step()
```

**De ce factorul `cos(heading_error)`?**
Dacă robotul are 90° față de țintă, `cos(90°) = 0`, deci nu se va deplasa liniar — va rota la fix mai întâi. Dacă e perfect aliniat, `cos(0) = 1`, deplasare la viteză maximă. Pe la mijloc, scalează lin.

**De ce pragul `align_threshold_rad`?**
Dublu safety: peste 30° de eroare, oprește total mișcarea liniară. Previne arce mari care îndepărtează robotul de țintă.

**Saturarea finală** asigură că nu depășim limitele fizice ale motoarelor.

---

## 8. Entry point — `main.py`

[src/main.py](coppeliasim-sim/src/main.py)

### 8.1 Argumente CLI

[src/main.py:62-74](coppeliasim-sim/src/main.py#L62-L74):
```python
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Navigare Pioneer P3-DX cu A*.")
    p.add_argument("--goal", nargs=2, type=float, required=True, metavar=("X", "Y"))
    p.add_argument("--map", type=Path, default=None)
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=23000)
    p.add_argument("--inflate", type=int, default=1)
    p.add_argument("--no-smooth", action="store_true")
    return p.parse_args()
```

### 8.2 Hartă din JSON

Format așteptat (vezi [scenes/map.json](coppeliasim-sim/scenes/map.json)):

```json
{
  "name": "Pioneer Maze 20x20",
  "rows": 20,
  "cols": 20,
  "cell_size": 0.25,
  "origin": [-2.5, -2.5],
  "obstacles": [
    [5, 3, 5, 12],
    [10, 8, 15, 8],
    [13, 2, 13, 14]
  ]
}
```

Fiecare obstacol e un dreptunghi de celule `[r1, c1, r2, c2]`. Loaderul îl marchează pe `occupancy`:

[src/main.py:39-59](coppeliasim-sim/src/main.py#L39-L59).

### 8.3 Pipeline executiv

[src/main.py:77-121](coppeliasim-sim/src/main.py#L77-L121):
```python
def main() -> int:
    args = parse_args()

    grid_map = load_map_from_json(args.map) if args.map else build_default_map()
    if args.inflate > 0:
        grid_map.inflate_obstacles(args.inflate)

    pathfinder = AStarPathfinder(grid_map)
    controller = PioneerController(host=args.host, port=args.port)

    controller.connect()
    controller.start_simulation()

    try:
        x, y, _ = controller.get_pose()
        start_cell = grid_map.world_to_grid(x, y)
        goal_cell = grid_map.world_to_grid(*args.goal)

        cells = pathfinder.find_path(start_cell, goal_cell)
        if not args.no_smooth:
            cells = AStarPathfinder.smooth_path(cells, grid_map)
        waypoints = [grid_map.grid_to_world(c) for c in cells]

        executor = PathExecutor(controller)
        success = executor.follow(waypoints)
        return 0 if success else 2
    finally:
        controller.stop()
        controller.stop_simulation()
        controller.disconnect()
```

`try/finally` garantează că robotul se oprește și se deconectează indiferent dacă pipeline-ul reușește sau eșuează — esențial ca scena să nu rămână cu motoarele pornite.

---

## 9. Cum se rulează

### 9.1 Cerințe

- **CoppeliaSim** (versiune cu suport ZMQ Remote API).
- Scena `pioneer_maze.ttt` cu un Pioneer P3-DX importat din library și obstacole. Vezi [scenes/README.md](coppeliasim-sim/scenes/README.md) pentru construcție.
- Python cu `coppeliasim-zmqremoteapi-client`, `numpy`, `scipy` (pentru inflate).

### 9.2 Pași

1. Deschide CoppeliaSim și încarcă scena.
2. Apasă **▶** în CoppeliaSim pentru a porni simularea fizică.
3. Rulează scriptul Python:
   ```
   cd D:\ProiectIA\coppeliasim-sim
   python -m src.main --goal 2.0 2.0 --map scenes/map.json --inflate 1
   ```
4. Robotul calculează drumul, îl afișează în consolă, apoi se deplasează autonom la țintă.

### 9.3 Exemple

| Comandă | Ce face |
|---------|---------|
| `python -m src.main --goal 4.0 3.0` | Folosește harta default din `build_default_map()`. |
| `python -m src.main --goal 2.0 2.0 --map scenes/map.json` | Harta din JSON. |
| `python -m src.main --goal 2.0 2.0 --map scenes/map.json --inflate 2` | Buffer mai mare în jurul obstacolelor. |
| `python -m src.main --goal 2.0 2.0 --no-smooth` | Dezactivează string-pulling — drum pas cu pas. |
| `python -m src.main --goal 2.0 2.0 --port 23001` | Port ZMQ custom. |

---

## 10. Probleme frecvente

**Eroare: ZMQ connection refused**
- CoppeliaSim trebuie să ruleze și **simularea să fie pornită** (butonul ▶).
- Portul implicit e 23000. Dacă l-ai schimbat, folosește `--port`.

**Robotul intră în obstacole**
- Mărește `--inflate` (1 = 25 cm buffer pentru `cell_size=0.25m`).
- Verifică `scipy` instalat (`pip install scipy`).

**Robotul oscilează lângă waypoint**
- Mărește `waypoint_tolerance` în `ExecutorConfig` (până la jumătate din `cell_size`).
- Scade `kp_angular` dacă rotația e prea agresivă.

**Drumul are zig-zag pe diagonale**
- Asigură-te că folosești `smooth_path` (activ implicit; dezactivat cu `--no-smooth`).
- Mărește `--inflate` ca drumul să stea mai departe de pereți și `smooth_path` să poată elimina mai mulți pași.

**Nu există drum**
- `NoPathFoundError` — apare dacă start sau goal sunt în obstacole, sau dacă inflate închide toate culoarele. Redu `--inflate` sau redefinește obstacolele.

---

## 11. Extinderi posibile

Idei pentru viitor (nu sunt implementate):

- **Senzori virtuali** (lidar/sonar): citește obstacole detectate live în loc de hartă pre-cunoscută → SLAM/D\* Lite.
- **Multi-robot**: extinde `PathExecutor` cu coordonare (rezervare celule, time-augmented A\*).
- **Cinematică suplimentară**: înlocuiește controlul P cu un Pure Pursuit sau MPC pentru urmărire mai fină.
- **Vizualizare live a drumului în CoppeliaSim**: desenează waypoints ca puncte 3D în scenă cu `sim.addDrawingObject`.
- **Integrare cu TSP app**: A\* găsește drumuri între orașe → cost real (nu Euclidean) → algoritmii TSP rulează pe matricea de costuri reale, nu pe distanțe euclidiene.

---

## 12. Teste

[tests/test_astar.py](coppeliasim-sim/tests/test_astar.py) — teste unitare pentru:
- `GridMap` (conversii world↔grid, vecini, inflate).
- `AStarPathfinder` (caz simplu, fără drum, cu obstacole).
- `smooth_path` (verifică reducerea numărului de waypoints).

Rulare: `pytest tests/` din `coppeliasim-sim/`.

---

## 13. Glosar rapid

| Termen | Sens |
|--------|------|
| **Occupancy grid** | Matrice booleană unde fiecare celulă e ocupată sau liberă. |
| **8-vecinătate** | Mișcări permise în 8 direcții (sus/jos/stânga/dreapta + 4 diagonale). |
| **Admisibilă (euristică)** | h(n) ≤ cost real → A\* găsește soluția optimă. |
| **String-pulling** | Tehnică de smoothing care elimină waypoints intermediari cu line-of-sight. |
| **Tracțiune diferențială** | Robotul controlat prin diferența de viteze între 2 roți. |
| **Yaw** | Rotația în plan orizontal (în jurul axei verticale). |
| **ZMQ Remote API** | Protocol de comunicare al CoppeliaSim pentru control extern. |
| **Stepping mode** | Simularea avansează pas cu pas, comandat din Python. |
| **Inflate** | Dilatare a obstacolelor pentru a ține cont de raza fizică a robotului. |
