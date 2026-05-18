# Arhitectură tehnică

## Privire de ansamblu

Proiectul este organizat în două componente independente care împart un set comun de dependențe Python:

```
ProiectIA/
├── tsp-app/              ←  Componenta 1: GUI + algoritmi TSP
│   └── src/
│       ├── core/         ─  Modele de date (City, Tour, TSPProblem, Result)
│       ├── algorithms/   ─  6 algoritmi (Backtrack, HC, SA, GA, ACO, NN)
│       ├── io/           ─  Loaders (CSV/JSON/URL) + exporters
│       └── gui/          ─  Componente PyQt6
│
├── coppeliasim-sim/      ←  Componenta 2: Simulare robotică
│   └── src/
│       ├── world/        ─  GridMap (discretizarea mediului)
│       ├── algorithms/   ─  A* pathfinding
│       └── controller/   ─  Pioneer P3-DX wrapper + PathExecutor
│
├── docs/                 ─  Documentație și diagrame
├── notebooks/            ─  Jupyter / Colab pentru raportul comparativ
└── requirements.txt
```

## Principii arhitecturale

### 1. Separare clară de responsabilități

- **`core/`** nu depinde de **`gui/`** sau **`io/`** — modelele de date sunt pure Python + NumPy.
- **`algorithms/`** primesc `TSPProblem` și returnează `AlgorithmResult` — nu cunosc UI-ul.
- **`gui/`** este singurul care depinde de PyQt6 — codul algoritmic poate rula fără GUI (ex: în notebook-uri).

### 2. Polimorfism prin clasa de bază

Toți algoritmii moștenesc din [`TSPAlgorithm`](../tsp-app/src/algorithms/base.py). Aceasta permite:
- Adăugarea unui algoritm nou prin scrierea unei singure clase.
- Tratarea uniformă în GUI și în benchmark-uri.

### 3. Threading pentru GUI responsive

Algoritmii rulează într-un `QThread` ([`SolverWorker`](../tsp-app/src/gui/worker.py)) și raportează progres prin semnale Qt → UI-ul rămâne responsive chiar și pentru ACO sau Backtracking lung.

### 4. Performanță prin vectorizare NumPy

- Matricea de distanțe este pre-calculată o singură dată (`TSPProblem._compute_distance_matrix`).
- Lungimea unui tur: `dist[order, np.roll(order, -1)].sum()` — O(n) vectorizat.
- Delta pentru 2-opt: O(1) — doar 4 muchii implicate.

### 5. Configurarea dinamică a parametrilor

Panoul de parametri din GUI este generat automat din [`SCHEMA`](../tsp-app/src/gui/parameter_panel.py) — adăugarea unui parametru nou nu necesită modificări manuale de widget-uri.

## Fluxul de date — TSP

```
CSV/JSON/URL ──► load_cities_*() ──► TSPProblem
                                          │
                                          ▼
                                   distance_matrix
                                          │
                                          ▼
                          TSPAlgorithm.solve(problem)
                                          │
                                          ▼
                                  AlgorithmResult
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                         TourCanvas   CSV export   PNG plot
                          (GUI)      (Colab)      (Colab)
```

## Fluxul de date — CoppeliaSim

```
map.json ──► GridMap.from_array() ──► inflate_obstacles(R)
                                              │
                                              ▼
                                      AStarPathfinder
                                              │
              ┌─ start_xy ◄──── PioneerController.get_pose()
              ▼                                │
       find_path_world(start, goal)            │ ZMQ
              │                                │
              ▼                                ▼
        waypoints world ────► PathExecutor.follow(wp)
                                              │
                                              ▼
                              set_velocity(v_lin, v_ang) [P-control]
                                              │
                                              ▼
                                       Pioneer P3-DX
```

## Decizii cheie

| Decizie | Motivație |
|---------|-----------|
| PyQt6 (nu Tkinter) | Aspect profesional, suport excelent pentru custom-paint și threading. |
| NumPy în `Tour.length()` | n=100 orașe → calcul lungime în ~5 μs vs. ~150 μs cu Python pur. |
| Order Crossover (OX1) pentru GA | Preservă ordinea relativă — esențial pentru TSP unde permutările sunt sensibile la poziție. |
| Distanță Euclidiană pentru A* | Robotul Pioneer se rotește liber → mișcările diagonale sunt valide → Euclid este admisibilă (Manhattan ar supraestima costul). |
| String-pulling smoothing | Reduce mișcările de zig-zag generate de grid discrete. |
| Stepping mode în CoppeliaSim | Control determinist al timpului → controller P stabil indiferent de FPS-ul real. |
