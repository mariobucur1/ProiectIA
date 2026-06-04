# Documentație ProiectIA — Aplicația TSP (Comis-Voiajor)

Acest document descrie integral funcționalitatea aplicației TSP din `tsp-app/`, cu fragmente de cod pentru fiecare algoritm și componentă GUI. Fișierele referite folosesc linkuri către codul sursă.

---

## 1. Privire de ansamblu

Aplicația rezolvă problema Comis-Voiajorului (TSP) — dat un set de orașe cu coordonate 2D, găsește turul de lungime minimă care vizitează fiecare oraș exact o dată și se închide la punctul de plecare.

**Funcționalități principale:**
- 6 algoritmi (1 exact + 5 metaheuristici/euristici).
- GUI PyQt6 cu temă dark, fereastră principală + fereastră separată de **vizualizare live**.
- Încărcare date din **CSV / JSON locale**, **URL GitHub raw**, sau **preseturi publice** integrate.
- Vizualizare a turului în timp real cu **zoom & pan** (QGraphicsView).
- Grafic de **convergență live** (matplotlib) cu toolbar de zoom/save.
- Export rezultate în CSV și grafic de convergență în PNG.
- Worker thread separat — UI-ul rămâne responsive în timpul rulărilor lungi.

---

## 2. Structura proiectului

```
tsp-app/
├── src/
│   ├── main.py                      # Entry point: pornește aplicația Qt
│   ├── core/                        # Modelul de date TSP (independent de UI)
│   │   ├── city.py                  # Clasa City (id, name, x, y)
│   │   ├── tour.py                  # Clasa Tour (permutare cu cache de lungime)
│   │   ├── problem.py               # TSPProblem (orașe + matrice distanțe)
│   │   └── result.py                # AlgorithmResult (tur final + istoric)
│   ├── algorithms/                  # Algoritmii TSP
│   │   ├── base.py                  # Clasa abstractă TSPAlgorithm + AlgorithmConfig
│   │   ├── backtracking.py          # Exact: branch & bound
│   │   ├── nearest_neighbor.py      # Euristic greedy
│   │   ├── hill_climbing.py         # Optimizare locală 2-opt
│   │   ├── simulated_annealing.py   # Călire simulată
│   │   ├── genetic.py               # Algoritm genetic (OX1 + 2-opt)
│   │   └── aco.py                   # Ant Colony Optimization
│   ├── gui/                         # Interfață grafică PyQt6
│   │   ├── main_window.py           # Fereastra principală + toolbar
│   │   ├── canvas.py                # TourCanvas (preview cu QPainter)
│   │   ├── visualization_window.py  # Fereastră live cu QGraphicsView + matplotlib
│   │   ├── parameter_panel.py       # Panou dinamic de parametri per algoritm
│   │   └── worker.py                # QThread pentru rularea algoritmilor
│   └── io/                          # I/O date
│       ├── loaders.py               # CSV / JSON / URL
│       └── exporters.py             # Export CSV + grafic PNG
├── data/                            # Dataseturi exemplu
├── scripts/benchmark.py             # Rulare comparativă din linia de comandă
└── tests/                           # Teste unitare
```

---

## 3. Modelul de date (core)

### 3.1 City — un oraș

Reprezentare imutabilă: id, nume, coordonate x, y. Distanța se calculează cu hypot (Euclidean).

[src/core/city.py:9-20](tsp-app/src/core/city.py#L9-L20):
```python
@dataclass(frozen=True, slots=True)
class City:
    id: int
    name: str
    x: float
    y: float

    def distance_to(self, other: "City") -> float:
        return hypot(self.x - other.x, self.y - other.y)
```

### 3.2 Tour — un tur (permutare)

Stochează ordinea ca `np.ndarray` și cache-uiește lungimea (recalculează doar când e marcat `_dirty`). Oferă operatori in-place: `swap`, `reverse_segment` (mutarea 2-opt), `insert`.

[src/core/tour.py:34-46](tsp-app/src/core/tour.py#L34-L46):
```python
def length(self, distance_matrix: np.ndarray) -> float:
    if not self._dirty and self._length is not None:
        return self._length
    idx = self._order
    nxt = np.roll(idx, -1)
    self._length = float(distance_matrix[idx, nxt].sum())
    self._dirty = False
    return self._length
```

`np.roll(idx, -1)` produce vecinul fiecărui oraș în tur (cu wrap la închidere), iar indexarea vectorizată `distance_matrix[idx, nxt]` extrage toate distanțele dintr-o singură operație NumPy — mult mai rapid decât bucla Python.

### 3.3 TSPProblem — instanța problemei

Conține orașele și **pre-calculează matricea de distanțe n×n** (read-only) ca acces O(1) la orice distanță. Esențial pentru algoritmii care interoghează intens (Hill Climbing, ACO).

[src/core/problem.py:41-46](tsp-app/src/core/problem.py#L41-L46):
```python
def _compute_distance_matrix(self) -> np.ndarray:
    coords = np.array([(c.x, c.y) for c in self.cities], dtype=np.float64)
    diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
    matrix = np.sqrt(np.sum(diff ** 2, axis=-1))
    matrix.setflags(write=False)
    return matrix
```

Broadcast NumPy: `diff[i,j]` = `coords[i] - coords[j]` pentru toate perechile simultan, fără bucle.

### 3.4 AlgorithmResult — rezultatul rulării

Structură comună returnată de toți algoritmii: tur final, lungime, istoric de convergență, timp, iterații, extra info.

[src/core/result.py:11-26](tsp-app/src/core/result.py#L11-L26)

---

## 4. Algoritmii TSP

Toți algoritmii implementează interfața `TSPAlgorithm._solve()` din [src/algorithms/base.py](tsp-app/src/algorithms/base.py). Wrapper-ul `solve()` măsoară automat timpul, iar `_should_stop()` verifică limita de iterații + timeout.

[src/algorithms/base.py:47-56](tsp-app/src/algorithms/base.py#L47-L56):
```python
def solve(self, problem, progress_callback=None) -> AlgorithmResult:
    start = time.perf_counter()
    result = self._solve(problem, progress_callback)
    result.elapsed_seconds = time.perf_counter() - start
    return result
```

`progress_callback(iteration, length, tour)` e apelat periodic în interior — GUI-ul îl folosește pentru redesenul live al turului și pentru graficul de convergență.

### 4.1 Backtracking (exact)

Soluție exactă: explorează toate permutările cu **branch-and-bound** (taie ramuri care depășesc deja cel mai bun cost). Complexitate O(n!) — practic doar pentru n ≤ 13.

[src/algorithms/backtracking.py:49-78](tsp-app/src/algorithms/backtracking.py#L49-L78):
```python
def recurse(depth: int, current_length: float) -> None:
    nonlocal best_length, best_path, nodes_explored

    if self.config.time_limit_seconds is not None:
        if (time.perf_counter() - start_time) >= self.config.time_limit_seconds:
            return

    nodes_explored += 1

    if depth == n:
        total = current_length + dist[current_path[-1], current_path[0]]
        if total < best_length:
            best_length = total
            best_path = current_path.copy()
            history.append(best_length)
            if progress_callback:
                progress_callback(nodes_explored, best_length, Tour(best_path))
        return

    last = current_path[depth - 1]
    for city in range(n):
        if visited[city]:
            continue
        new_length = current_length + dist[last, city]
        if new_length >= best_length:           # PRUNING — branch and bound
            continue
        visited[city] = True
        current_path[depth] = city
        recurse(depth + 1, new_length)
        visited[city] = False
```

Pruning-ul de la `if new_length >= best_length: continue` este cheia eficienței: orice cale parțială care deja costă mai mult decât cea mai bună soluție completă găsită până acum se abandonează.

**Limita de n=13** se aplică prin verificare la intrare:

[src/algorithms/backtracking.py:35-39](tsp-app/src/algorithms/backtracking.py#L35-L39):
```python
if n > 13 and not self.config.extra.get("force", False):
    raise ValueError(
        f"Backtracking este impracticabil pentru n={n} (limită ~13). "
        "Setează config.extra['force']=True pentru a încerca oricum."
    )
```

În GUI există checkbox-ul **"Forțează pentru n > 13 (ATENȚIE: O(n!))"** care setează `force=True`.

### 4.2 Nearest Neighbor (greedy)

Construire greedy: pornește dintr-un oraș și la fiecare pas alege orașul nevizitat cel mai apropiat. O(n²), rapid, dă soluții ~25% peste optim. Util ca **start pentru Hill Climbing** și ca baseline.

[src/algorithms/nearest_neighbor.py:40-46](tsp-app/src/algorithms/nearest_neighbor.py#L40-L46):
```python
for step in range(1, n):
    row = dist[current].copy()
    row[visited] = np.inf      # invalidează orașele vizitate
    nxt = int(np.argmin(row))  # cel mai apropiat dintre cele rămase
    path[step] = nxt
    visited[nxt] = True
    current = nxt
```

### 4.3 Hill Climbing (2-opt)

Strategia "alpinistului": pornește de la o soluție inițială (random sau NN) și încearcă mutări locale **2-opt** (inversează un segment). Se oprește în optim local. **Random restart** ajută să scape de optime locale.

**Cheia eficienței** — evaluare O(1) a unei mutări 2-opt (nu re-calculează tot turul):

[src/algorithms/hill_climbing.py:110-123](tsp-app/src/algorithms/hill_climbing.py#L110-L123):
```python
@staticmethod
def _two_opt_delta(order, i, j, dist, n) -> float:
    """Schimbarea de cost dacă inversăm segmentul [i..j]."""
    a, b = order[i - 1], order[i]
    c, d = order[j], order[(j + 1) % n]
    if i == 0 and j == n - 1:
        return 0.0
    return dist[a, c] + dist[b, d] - dist[a, b] - dist[c, d]
```

Doar 2 muchii ies (a-b, c-d) și 2 intră (a-c, b-d) — restul segmentului rămâne identic, doar inversat.

**Bucla principală** alege fie prima vecinătate îmbunătățitoare (`first_improvement`) fie cea mai bună (`best_improvement`):

[src/algorithms/hill_climbing.py:60-87](tsp-app/src/algorithms/hill_climbing.py#L60-L87):
```python
improved = True
while improved:
    improved = False
    best_delta = 0.0
    best_move = None

    for i in range(n - 1):
        for j in range(i + 1, n):
            delta = self._two_opt_delta(tour.order, i, j, dist, n)
            if delta < best_delta - 1e-12:
                best_delta = delta
                best_move = (i, j)
                if strategy == "first_improvement":
                    break

    if best_move is not None:
        i, j = best_move
        tour.reverse_segment(i, j)
        current_length += best_delta
        improved = True
```

### 4.4 Simulated Annealing

Inspirat de călirea metalelor: la temperaturi mari acceptă mutări proaste pentru a scăpa din optime locale; pe măsură ce temperatura scade, devine "greedy".

**Criteriul de acceptare** — formula Metropolis:

[src/algorithms/simulated_annealing.py:67-73](tsp-app/src/algorithms/simulated_annealing.py#L67-L73):
```python
if delta < 0 or rng.random() < math.exp(-delta / temperature):
    tour.reverse_segment(i, j)
    current_length += delta
    accepted += 1
    if current_length < best_length - 1e-9:
        best_length = current_length
        best_tour = tour.copy()
```

- `delta < 0`: îmbunătățire — întotdeauna acceptat.
- `delta > 0`: deteriorare — acceptată cu probabilitatea `exp(-Δ/T)`. La T mare, probabilitatea e aproape 1; la T mic, aproape 0.

**Schema de răcire** geometrică: `T_{k+1} = T_k × cooling_rate` (tipic 0.995).

**Temperatura inițială auto** — estimată din abaterea costurilor unor mutări aleatoare, astfel încât ~80% din mutările proaste să fie acceptate la început:

[src/algorithms/simulated_annealing.py:103-125](tsp-app/src/algorithms/simulated_annealing.py#L103-L125)

### 4.5 Genetic Algorithm

Evolutiv — populație de tururi care se reproduc, mutează și se selectează pe baza calității.

**Componentele:**
- **Selecție**: tournament (k indivizi aleatori, cel mai bun trece).
- **Crossover**: Order Crossover (OX1) — păstrează ordinea relativă din ambii părinți.
- **Mutație**: 2-opt swap cu probabilitatea `pm`.
- **Elitism**: top E indivizi trec direct în următoarea generație.

**Tournament selection:**

[src/algorithms/genetic.py:120-125](tsp-app/src/algorithms/genetic.py#L120-L125):
```python
@staticmethod
def _tournament_select(rng, fitness, k) -> int:
    candidates = rng.choice(len(fitness), size=k, replace=False)
    return int(candidates[np.argmin(fitness[candidates])])
```

**Order Crossover (OX1):**

[src/algorithms/genetic.py:127-149](tsp-app/src/algorithms/genetic.py#L127-L149):
```python
@staticmethod
def _order_crossover(parent1, parent2, rng) -> np.ndarray:
    n = len(parent1)
    a, b = sorted(rng.choice(n, size=2, replace=False).tolist())
    child = np.full(n, -1, dtype=np.int32)
    child[a : b + 1] = parent1[a : b + 1]      # copiază segmentul din p1

    in_segment = np.zeros(n, dtype=bool)
    in_segment[parent1[a : b + 1]] = True

    fill_pos = (b + 1) % n
    for city in np.roll(parent2, -(b + 1)):    # ordinea din p2
        if not in_segment[city]:
            child[fill_pos] = city
            fill_pos = (fill_pos + 1) % n
    return child
```

Ideea OX1: păstrează un segment continuu din primul părinte și completează restul în ordinea în care apar orașele în al doilea părinte (sărind peste cele deja prezente). Astfel copilul moștenește ordinea relativă, esențială pentru TSP.

**Bucla evoluției** cu elitism:

[src/algorithms/genetic.py:62-88](tsp-app/src/algorithms/genetic.py#L62-L88):
```python
for generation in range(max_generations):
    sorted_idx = np.argsort(fitness)
    new_population = np.empty_like(population)
    new_fitness = np.empty_like(fitness)
    new_population[:elite_count] = population[sorted_idx[:elite_count]]
    new_fitness[:elite_count] = fitness[sorted_idx[:elite_count]]

    for k in range(elite_count, population_size):
        p1 = self._tournament_select(rng, fitness, tournament_k)
        p2 = self._tournament_select(rng, fitness, tournament_k)

        if rng.random() < crossover_rate:
            child = self._order_crossover(population[p1], population[p2], rng)
        else:
            child = population[p1].copy()

        if rng.random() < mutation_rate:
            self._mutate_two_opt(child, rng)

        new_population[k] = child
        new_fitness[k] = self._tour_length(child, dist)

    population = new_population
    fitness = new_fitness
```

### 4.6 Ant Colony Optimization (ACO)

Bio-inspirat — furnicile depun feromon pe drumurile bune, ceea ce atrage alte furnici. Implementarea de aici este **Ant System** clasic (Dorigo, 1992).

**Regula probabilistică** — orașul următor se alege cu probabilitatea:

```
P(i → j) = (τ_ij^α · η_ij^β) / Σ_k (τ_ik^α · η_ik^β)
```

unde `τ` e feromonul și `η = 1/distanță` e vizibilitatea. `α` controlează importanța feromonului, `β` importanța distanței.

[src/algorithms/aco.py:113-146](tsp-app/src/algorithms/aco.py#L113-L146):
```python
@staticmethod
def _construct_tour(rng, pheromone, visibility, alpha, beta, n) -> np.ndarray:
    tour = np.empty(n, dtype=np.int32)
    unvisited = np.ones(n, dtype=bool)
    start = int(rng.integers(0, n))
    tour[0] = start
    unvisited[start] = False
    current = start

    for step in range(1, n):
        tau = pheromone[current] ** alpha
        eta = visibility[current] ** beta
        scores = tau * eta
        scores[~unvisited] = 0.0
        total = scores.sum()
        if total <= 0.0:
            choices = np.where(unvisited)[0]
            nxt = int(rng.choice(choices))
        else:
            probs = scores / total
            nxt = int(rng.choice(n, p=probs))
        tour[step] = nxt
        unvisited[nxt] = False
        current = nxt

    return tour
```

**Update-ul feromonului** după fiecare iterație:

[src/algorithms/aco.py:81-87](tsp-app/src/algorithms/aco.py#L81-L87):
```python
pheromone *= 1.0 - rho        # evaporare globală
for k in range(num_ants):
    deposit = Q / all_lengths[k]   # depunere proporțională cu calitatea
    t = all_tours[k]
    nxt = np.roll(t, -1)
    pheromone[t, nxt] += deposit
    pheromone[nxt, t] += deposit
```

Evaporarea (`ρ`) împiedică convergența prematură; depunerea proporțională cu `1/lungime` recompensează tururile scurte.

---

## 5. Interfața grafică

### 5.1 Fereastra principală — `MainWindow`

[src/gui/main_window.py](tsp-app/src/gui/main_window.py)

Layout:
```
┌────────────────────────────────────────────────────────┐
│ Toolbar: Încarcă CSV/JSON/URL | Dataseturi publice ▾ |  │
│          🔍 Vizualizare live | ▶ Rulează | ■ Oprește |  │
│          Export CSV | Export grafic                     │
├──────────────┬─────────────────────────────────────────┤
│              │                                          │
│  Sidebar:    │      TourCanvas (preview)                │
│  Algoritm ▾  │      (vizualizare 2D cu QPainter)        │
│  Parametri   │                                          │
│  Rezultate   │                                          │
├──────────────┴─────────────────────────────────────────┤
│  Status bar: iter | lungime | timp                      │
└────────────────────────────────────────────────────────┘
```

**Toolbar — butoane:**
- **Încarcă CSV…** — fișier local cu header `id,name,x,y` (sau headerless).
- **Încarcă JSON…** — fișier local cu structură `{cities: [...]}`.
- **Încarcă de pe GitHub…** — orice URL raw.
- **Dataseturi publice ▾** — meniu dropdown cu 4 preseturi (acu192 tiny/small/medium/large).
- **🔍 Vizualizare live** — deschide fereastra separată.
- **▶ Rulează** / **■ Oprește** — pornește/oprește algoritmul (deschide automat fereastra de vizualizare).
- **Export CSV rezultate** / **Export grafic convergență** — salvează rezultatele.

**Lansarea unui algoritm** — pornește workerul în thread separat și conectează semnalele:

[src/gui/main_window.py:264-281](tsp-app/src/gui/main_window.py#L264-L281):
```python
config = AlgorithmConfig()
if "max_iterations" in params:
    config.max_iterations = int(params.pop("max_iterations"))
if "time_limit_seconds" in params:
    config.time_limit_seconds = float(params.pop("time_limit_seconds"))
config.extra = params

algorithm = ALGORITHMS[name](config)
self._worker = SolverWorker(algorithm, self._problem, self)
self._worker.progress.connect(self._on_progress)
self._worker.finished_with_result.connect(self._on_finished)
self._worker.error.connect(self._on_error)

viz = self._ensure_viz_window()
viz.start_run(name)
...
self._worker.start()
```

### 5.2 Panoul de parametri — `ParameterPanel`

[src/gui/parameter_panel.py](tsp-app/src/gui/parameter_panel.py)

Generează **dinamic** câmpurile de input pe baza unei SCHEMA: dict[algoritm → {param → spec}]. Când userul schimbă algoritmul din combo, panoul se reconstruiește.

**Specul unui parametru** — clasa `ParamSpec`:

[src/gui/parameter_panel.py:27-38](tsp-app/src/gui/parameter_panel.py#L27-L38):
```python
@dataclass
class ParamSpec:
    label: str
    kind: str               # "int" / "float" / "bool"
    default: Any
    minimum: float = 0.0
    maximum: float = 1e9
    step: float = 1.0
    decimals: int = 3
    tooltip: str = ""
```

**Exemplu de SCHEMA** pentru Simulated Annealing:

[src/gui/parameter_panel.py:60-66](tsp-app/src/gui/parameter_panel.py#L60-L66):
```python
"Simulated Annealing": {
    "max_iterations": ParamSpec("Iterații maxime", "int", 100_000, 100, 10_000_000),
    "initial_temp": ParamSpec("Temperatură inițială (0 = auto)", "float", 0.0, 0.0, 1e6, 1.0, 2),
    "final_temp": ParamSpec("Temperatură finală", "float", 0.001, 1e-6, 100.0, 0.001, 6),
    "cooling_rate": ParamSpec("Rata de răcire", "float", 0.995, 0.8, 0.9999, 0.001, 4),
},
```

Pentru fiecare spec, `_build_widget()` returnează un `QSpinBox`, `QDoubleSpinBox` sau `QCheckBox` configurat. `get_values()` extrage la final dict-ul `{key: value}` care e băgat în `config.extra`. Astfel **adăugarea unui parametru nou** necesită doar o intrare în SCHEMA — UI-ul se generează automat.

### 5.3 Worker thread — `SolverWorker`

[src/gui/worker.py](tsp-app/src/gui/worker.py)

`QThread` care rulează algoritmul în afara thread-ului UI, ca să nu blocheze interfața în timpul rulărilor lungi (Backtracking pe 20 orașe, ACO etc.).

[src/gui/worker.py:26-53](tsp-app/src/gui/worker.py#L26-L53):
```python
class SolverWorker(QThread):
    progress = pyqtSignal(int, float, object)
    finished_with_result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, algorithm, problem, parent=None):
        super().__init__(parent)
        self._algorithm = algorithm
        self._problem = problem
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True
        self._algorithm.config.time_limit_seconds = 0.001

    def run(self) -> None:
        try:
            result = self._algorithm.solve(
                self._problem,
                progress_callback=self._on_progress,
            )
            self.finished_with_result.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
```

**Trucul pentru Stop**: `request_stop()` setează un time_limit foarte mic — algoritmul se va opri la următoarea verificare `_should_stop()`, fără a-l forța prin omor de thread.

### 5.4 Canvas preview — `TourCanvas`

[src/gui/canvas.py](tsp-app/src/gui/canvas.py)

Widget custom-paint cu `QPainter`. Afișează:
- Orașele ca cercuri (cel de start în roșu).
- Turul curent (verde) suprapus peste cel mai bun (galben, semi-transparent).
- Text cu numele orașelor (opțional) și info-line cu lungimea curentă.
- Auto-scaling să încadreze toate orașele în zonă.

[src/gui/canvas.py:93-114](tsp-app/src/gui/canvas.py#L93-L114) — transformarea coordonate lume → coordonate ecran.

E ușor și rapid, dar **fără zoom/pan**. Pentru zoom folosește fereastra de vizualizare live.

### 5.5 Fereastra de vizualizare live — `VisualizationWindow`

[src/gui/visualization_window.py](tsp-app/src/gui/visualization_window.py)

Fereastra separată non-modală, deschisă la Run. Conține:
- **Stânga**: `TourGraphicsView` — `QGraphicsView` cu zoom pe scroll wheel și pan cu drag.
- **Dreapta**: `FigureCanvasQTAgg` matplotlib cu graficul de convergență + `NavigationToolbar2QT` (zoom rectangle, pan, home, save PNG).
- **Sus**: butoane Reset zoom, checkbox etichete orașe, label de stare cu iter/best/timp.

**Zoom-ul pe turul TSP** — implementat cu wheel event scale:

[src/gui/visualization_window.py:169-174](tsp-app/src/gui/visualization_window.py#L169-L174):
```python
def wheelEvent(self, event) -> None:
    angle = event.angleDelta().y()
    if angle == 0:
        return
    factor = 1.15 if angle > 0 else 1 / 1.15
    self.scale(factor, factor)
```

`setTransformationAnchor(AnchorUnderMouse)` face zoom-ul să se centreze pe cursor.

**Update live al turului** — `QGraphicsPathItem` reutilizat (nu re-creat) la fiecare progres:

[src/gui/visualization_window.py:121-133](tsp-app/src/gui/visualization_window.py#L121-L133):
```python
def set_tour(self, tour) -> None:
    if self._problem is None or tour is None:
        return
    path = self._build_path(tour)
    if self._tour_item is None:
        pen = QPen(_TOUR, 2.0)
        pen.setCosmetic(True)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self._tour_item = self._scene.addPath(path, pen)
        self._tour_item.setZValue(1)
    else:
        self._tour_item.setPath(path)
```

`setCosmetic(True)` pe pen: grosimea liniei rămâne constantă indiferent de zoom.

**Update live al graficului** — throttled la ~7 fps ca să nu blocheze UI-ul:

[src/gui/visualization_window.py:248-262](tsp-app/src/gui/visualization_window.py#L248-L262):
```python
def on_progress(self, iteration, length, tour) -> None:
    self._tour_view.set_tour(tour)
    self._convergence.append(length)
    if length < self._best_length:
        self._best_length = length

    now = time.perf_counter()
    if now - self._last_plot_redraw > self.PLOT_REDRAW_INTERVAL:
        self._redraw_plot()
        self._last_plot_redraw = now
```

Graficul afișează două curbe: lungimea curentă (verde) și running-best (galben, punctată).

---

## 6. Încărcare și export date

### 6.1 Loadere

[src/io/loaders.py](tsp-app/src/io/loaders.py)

Trei funcții publice:
- `load_cities_from_csv(path)` — fișier CSV local.
- `load_cities_from_json(path)` — fișier JSON local.
- `load_cities_from_url(url)` — descarcă cu `requests` și detectează formatul după extensie.

**Format CSV standard** (cu header):
```
id,name,x,y
0,Suceava,26.25,47.64
1,Iasi,27.59,47.16
```

**Format CSV headerless** (auto-detectat dacă prima linie are doar numere):

[src/io/loaders.py:103-114](tsp-app/src/io/loaders.py#L103-L114):
```python
def _row_is_numeric(line: str) -> bool:
    fields = [f.strip() for f in line.split(",") if f.strip() != ""]
    if not fields:
        return False
    for f in fields:
        try:
            float(f)
        except ValueError:
            return False
    return True
```

Dacă prima linie e numerică, parser-ul tratează:
- 2 coloane → `x,y` (id auto-generat).
- 3+ coloane → `id,x,y`.

Așa pot fi încărcate dataseturile **acu192** (CSV-uri fără header, doar numere).

### 6.2 Preseturi GitHub

[src/gui/main_window.py:58-79](tsp-app/src/gui/main_window.py#L58-L79):
```python
REMOTE_PRESETS: list[tuple[str, str, str]] = [
    ("acu192 — tiny (10 orașe)",
     "https://raw.githubusercontent.com/acu192/fun-tsp-challenge/master/data/tiny.csv",
     "acu192-tiny-10"),
    ("acu192 — small (30 orașe, clusterizate)", ..., "acu192-small-30"),
    ("acu192 — medium (100 orașe)", ..., "acu192-medium-100"),
    ("acu192 — large (1000 orașe)", ..., "acu192-large-1000"),
]
```

Click pe oricare → descarcă raw URL → parsează → setează problema.

### 6.3 Exportere

[src/io/exporters.py](tsp-app/src/io/exporters.py)

- `export_result_to_csv(results, path)` — tabel comparativ (algoritm, lungime, timp, iterații).
- `export_history_plot(results, path)` — grafic matplotlib cu curbele de convergență ale tuturor rezultatelor din sesiune, salvat ca PNG.

---

## 7. Flux de utilizare tipic

1. **Pornire**: `python -m src.main` (din `tsp-app/` cu venv-ul activat).
2. **Încărcare date**: alege CSV/JSON local sau un preset GitHub.
3. **Selectare algoritm**: din combo-ul "Algoritm" din sidebar.
4. **Reglare parametri**: panoul se reconstruiește automat per algoritm.
5. **Rulează**: butonul ▶ → workerul pornește, fereastra de vizualizare se deschide.
6. **Live**: vezi turul evoluând cu zoom/pan, graficul de convergență live.
7. **Stop opțional**: ■ Oprește (algoritm se oprește la următorul check).
8. **Repetare**: schimbă parametrii/algoritmul și apasă din nou ▶ — rezultatele se acumulează.
9. **Export**: salvează CSV-ul cu toate rezultatele sau PNG-ul cu convergența.

---

## 8. Extinderea cu un algoritm nou

Pași minimi pentru a adăuga un algoritm:

1. **Implementează** într-un fișier nou în `src/algorithms/`:
   ```python
   class MyAlgorithm(TSPAlgorithm):
       name = "Algoritmul meu"
       def _solve(self, problem, progress_callback):
           # ... logică ...
           return AlgorithmResult(algorithm_name=self.name, best_tour=..., ...)
   ```
2. **Înregistrează-l** în `src/algorithms/__init__.py`:
   ```python
   ALGORITHMS["Algoritmul meu"] = MyAlgorithm
   ```
3. **Adaugă parametri** în `src/gui/parameter_panel.py` SCHEMA:
   ```python
   "Algoritmul meu": {
       "param1": ParamSpec("Etichetă", "int", default=10, ...),
   },
   ```

Atât — UI-ul îl detectează automat. Combo-ul îl listează, panoul de parametri îl populează cu câmpurile, worker-ul îl rulează în thread separat.

---

## 9. Dependențe

Din [requirements.txt](requirements.txt):
- `PyQt6` — GUI.
- `numpy` — vectorizare matrice de distanțe + tururi.
- `matplotlib` — grafic de convergență + export PNG.
- `requests` — descărcare date de pe URL-uri.
- `pytest` — teste unitare.

---

## 10. Teste

[tests/](tsp-app/tests):
- `test_core.py` — Tour, TSPProblem, calcul lungimi, cache, mutări.
- `test_algorithms.py` — fiecare algoritm produce un tur valid pe instanțe mici.

Rulare: `pytest tests/` din directorul `tsp-app/`.
