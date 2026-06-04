# CoppeliaSim Sim — robot diferențial + A* + Reinforcement Learning

Componenta de simulare robotică: un robot diferențial (`Diff_Drive_Bot`) în CoppeliaSim parcurge labirintul **Arena.ttt**. Robotul ajunge de la START la STOP în două moduri:
- **A\*** — planificare clasică pe grid (deterministă).
- **Reinforcement Learning (Q-learning)** — robotul **învață singur** ruta într-un mediu grid rapid, apoi politica învățată este transferată în CoppeliaSim ([detalii mai jos](#reinforcement-learning--robotul-învață-labirintul)).

Controllerul Python comunică cu CoppeliaSim prin ZMQ Remote API.

## Pornire rapidă

1. **Deschide CoppeliaSim** și încarcă scena `scenes/Arena.ttt`.
2. **Generează harta** din geometria pereților (o singură dată, cu scena încărcată):
   ```bash
   cd D:\ProiectIA\coppeliasim-sim
   python build_map.py            # scrie scenes/arena_auto.json
   ```
3. **Pornește simularea** (butonul ▶ din CoppeliaSim).
4. **Rulează A\*** (drum determinist):
   ```bash
   python -m src.main --goal 0.75 0.23 --map scenes/arena_auto.json --inflate 1
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

## Reinforcement Learning — robotul învață labirintul

În loc să i se dea drumul, robotul **învață singur** ruta de la START la STOP prin **Q-learning tabular**, antrenat într-un mediu grid rapid (headless), apoi politica este transferată în CoppeliaSim.

### De ce antrenare headless?

Antrenarea în CoppeliaSim real-time ar dura ore (fiecare episod rulează în timp fizic). În schimb, mediul `MazeEnv` rulează mii de episoade în câteva secunde pe aceeași hartă (`arena_auto.json`), apoi robotul real execută **o singură dată** drumul învățat.

### Flux complet

```bash
cd D:\ProiectIA\coppeliasim-sim

# 1. (cu Arena.ttt încărcată) generează harta din pereți
python build_map.py

# 2. antrenează agentul (headless, ~secunde) — salvează models/q_table.npy + learning_curve.png
python -m src.rl.train --episodes 2000

# 3. (cu simularea pornită) transferă politica în CoppeliaSim — robotul rezolvă labirintul
python -m src.rl.deploy --screenshot models/solved_topview.png
python -m src.rl.deploy --dry-run        # doar afișează drumul învățat, fără robot
```

### Componente ([src/rl/](src/rl/))

| Fișier | Rol |
|--------|-----|
| `maze_env.py` | Mediu grid (stil Gym): stare = celulă, 4 acțiuni, recompense (țintă +10, pas −0.05, coliziune −0.75) |
| `qlearning.py` | Agent Q-learning tabular: Q(s,a) ← Q(s,a) + α·[r + γ·maxₐ Q(s',a') − Q(s,a)], explorare ε-greedy |
| `scene_map.py` | Încărcarea hărții + celule start/goal + render ASCII (sursă unică de adevăr) |
| `train.py` | Bucla de antrenare + curba de învățare + drumul greedy în ASCII |
| `deploy.py` | Politică → drum de celule → colțuri → waypoints world → `PathExecutor` în CoppeliaSim |

### Recompensă (reward shaping)

| Eveniment | Recompensă | Scop |
|-----------|-----------:|------|
| Atinge STOP | +10.0 | Obiectivul |
| Pas normal | −0.05 | Împinge spre drumul cel mai scurt |
| Coliziune cu perete | −0.75 | Descurajează ciocnirile |

Robotul învață ruta exactă START→A→B→C→D→E→F→G→H→I→STOP — aceeași cu traseul de referință desenat în scenă, dar **descoperită singur**.

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
