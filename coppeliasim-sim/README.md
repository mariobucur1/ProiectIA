# CoppeliaSim Sim — Pioneer P3-DX + A*

Componenta de simulare robotică: un robot **Pioneer P3-DX** în CoppeliaSim parcurge un mediu cu obstacole folosind algoritmul **A\*** și un controller Python care comunică prin ZMQ Remote API.

## Pornire rapidă

1. **Deschide CoppeliaSim** și încarcă scena `scenes/pioneer_maze.ttt` (vezi [scenes/README.md](scenes/README.md) pentru construcția scenei).
2. **Pornește simularea** (butonul ▶ din CoppeliaSim).
3. **Rulează scriptul Python**:
   ```bash
   cd D:\ProiectIA\coppeliasim-sim
   python -m src.main --goal 2.0 2.0 --map scenes/map.json --inflate 1
   ```

## Algoritm A* — detalii ([src/algorithms/astar.py](src/algorithms/astar.py))

| Componentă | Implementare |
|------------|-------------|
| **Funcție de evaluare** | f(n) = g(n) + h(n) |
| **g(n)** | Cost real acumulat (1.0 ortogonal, √2 diagonal) |
| **h(n)** | **Distanța Euclidiană** (admisibilă pentru robotul Pioneer) |
| **Vecinătate** | 8-vecini (cu verificare anti corner-cutting) |
| **Structură open** | Min-heap (heapq) cu tie-breaking prin contor |
| **Smoothing** | String-pulling cu Bresenham line-of-sight |

### De ce Distanța Euclidiană?

Robotul Pioneer P3-DX se poate roti liber, deci nu este restricționat la direcții perpendiculare. O linie dreaptă între două puncte este întotdeauna ≤ orice drum real → euristica nu supraestimează costul (este admisibilă) → A* este garantat optimal.

## Pipeline complet

```
┌─────────────────┐
│   GridMap       │  rows × cols, cell_size, origin
│ (occupancy)     │  Obstacle inflation cu raza robot
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AStarPathfinder │  find_path(start, goal) → list[GridCell]
│ + smooth_path() │  Reduce zig-zag-ul pe diagonale
└────────┬────────┘
         │ waypoints world (x, y)
         ▼
┌─────────────────┐
│   PathExecutor  │  Control P pe (heading_error, distance_error)
│   (KP_lin/ang)  │  Reduce viteza liniară când nu e aliniat
└────────┬────────┘
         │ v_linear, v_angular
         ▼
┌─────────────────┐
│   Pioneer       │  Diferențială: convertește (v, ω) → (v_left, v_right)
│   Controller    │  ZMQ Remote API → CoppeliaSim
└─────────────────┘
```

## Structură cod

```
src/
├── world/
│   └── grid_map.py     # GridMap (rows, cols, occupancy, conversii world↔grid)
├── algorithms/
│   └── astar.py        # AStarPathfinder + smooth_path (Bresenham LOS)
├── controller/
│   ├── pioneer.py      # Wrapper ZMQ pentru Pioneer P3-DX
│   └── path_executor.py # Control P pentru urmărirea waypoints-urilor
└── main.py             # Entry point CLI
scenes/
├── map.json            # Definiția hărții 20×20
└── README.md           # Cum se construiește scena .ttt
```

## Parametri tunabili pentru navigare

În `src/controller/path_executor.py → ExecutorConfig`:

| Parametru | Implicit | Rol |
|-----------|---------:|-----|
| `kp_linear` | 0.8 | Câștig pentru distanță. Mai mare = mai rapid, dar oscilează. |
| `kp_angular` | 2.5 | Câștig pentru orientare. Robotul trebuie să se alinieze rapid. |
| `max_linear` | 0.4 m/s | Limită fizică superioară pentru viteza liniară. |
| `max_angular` | 1.5 rad/s | Limită pentru rotație. |
| `align_threshold_rad` | 30° | Sub acest unghi robotul accelerează liniar. |
| `waypoint_tolerance` | 0.12 m | Distanță până la waypoint pentru a trece la următorul. |
| `final_tolerance` | 0.10 m | Toleranță mai strictă pentru ținta finală. |

## Probleme frecvente

**Eroare: ZMQ connection refused**
- Verifică că CoppeliaSim rulează și că simularea este **pornită** (butonul ▶).
- Portul implicit este 23000. Dacă l-ai schimbat, folosește `--port`.

**Robotul intră în obstacole**
- Mărește `--inflate` (1 = 25 cm buffer pentru `cell_size=0.25m`).
- Verifică `scipy` instalat (necesită `pip install scipy`).

**Robotul oscilează lângă waypoint**
- Mărește `waypoint_tolerance` (până la jumătate din `cell_size`).
- Scade `kp_angular` dacă rotația este prea agresivă.

**Drumul are zig-zag pe diagonale**
- Asigură-te că folosești `smooth_path` (activ implicit; dezactivat doar cu `--no-smooth`).
