# TSP App — Aplicație Python GUI pentru Comis-Voiajor

Aplicație **PyQt6** care rezolvă problema Comis-Voiajorului (TSP) prin 6 algoritmi diferiți. Permite încărcarea datelor din fișiere locale sau direct de pe GitHub, vizualizarea în timp real a soluției și exportul rezultatelor pentru raportul comparativ.

## Pornire rapidă

```bash
cd D:\ProiectIA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd tsp-app
python -m src.main
```

## Algoritmi implementați

### 1. Backtracking recursiv ([src/algorithms/backtracking.py](src/algorithms/backtracking.py))
- **Tip**: Exact (cu branch-and-bound)
- **Complexitate**: O(n!) — practic doar pentru n ≤ 12
- **Garanție**: Găsește soluția optimă
- **Pruning**: Renunță la ramuri cu cost ≥ best_length cunoscut

### 2. Hill Climbing ([src/algorithms/hill_climbing.py](src/algorithms/hill_climbing.py))
- **Tip**: Căutare locală
- **Operator**: 2-opt swap (inversare segment, O(1) delta)
- **Strategii**: `best_improvement` / `first_improvement`
- **Restart**: Random restart pentru a scăpa de optime locale
- **Pornire**: Opțional de la soluția Nearest Neighbor

### 3. Simulated Annealing ([src/algorithms/simulated_annealing.py](src/algorithms/simulated_annealing.py))
- **Tip**: Stochastic, inspirat de călirea metalelor
- **Schemă răcire**: Geometrică (T ← T · cooling_rate)
- **Probabilitate acceptare**: P = exp(−ΔE / T)
- **Temperatura inițială**: Auto-calculată pentru ~80% acceptare inițială

### 4. Algoritm Genetic ([src/algorithms/genetic.py](src/algorithms/genetic.py))
- **Selecție**: Tournament (k = 5)
- **Crossover**: Order Crossover (OX1) — păstrează ordinea relativă
- **Mutație**: 2-opt segment reverse
- **Elitism**: Top E indivizi trec direct în următoarea generație

### 5. Ant Colony Optimization ([src/algorithms/aco.py](src/algorithms/aco.py))
- **Variantă**: Ant System (Dorigo, 1992)
- **Probabilitate alegere**: P(i→j) ∝ τ_ij^α · η_ij^β
- **Feromon inițial**: τ₀ = m / L_NN (m furnici, L_NN lungime NN)
- **Evaporare**: τ ← (1−ρ) · τ după fiecare iterație

### 6. Nearest Neighbor ([src/algorithms/nearest_neighbor.py](src/algorithms/nearest_neighbor.py))
- **Tip**: Greedy heuristic (baseline)
- **Complexitate**: O(n²)
- **Calitate**: Tipic ~25% peste optim

## Structură cod

```
src/
├── core/                # Modele de date
│   ├── city.py          # Oraș (id, name, x, y)
│   ├── tour.py          # Tur cu operații vectorizate NumPy
│   ├── problem.py       # Instanța TSP + matrice distanțe pre-calculată
│   └── result.py        # Rezultat standardizat (lungime, timp, istoric)
├── algorithms/          # Cei 6 algoritmi
│   ├── base.py          # TSPAlgorithm (interfață) + AlgorithmConfig
│   └── …
├── io/                  # Loaders (CSV/JSON/URL) + exporters
└── gui/                 # Componente PyQt6
    ├── main_window.py   # Fereastra principală + toolbar
    ├── canvas.py        # Custom-paint pentru vizualizare 2D
    ├── parameter_panel.py  # Panou dinamic de parametri pe algoritm
    └── worker.py        # QThread pentru rulări fără blocaj UI
```

## Workflow în GUI

1. **Toolbar → Încarcă CSV / JSON / GitHub** — selectează un set de date
2. **Sidebar → Algoritm** — alege unul din cei 6 algoritmi
3. **Panou Parametri** — ajustează parametrii (apar dinamic în funcție de algoritm)
4. **Toolbar → ▶ Rulează** — pornește algoritmul (rulează pe thread separat)
5. **Canvas** — vizualizează turul curent în timp real
6. **Toolbar → Export CSV / grafic convergență** — pentru raportul Colab

## Adăugarea unui algoritm nou

1. Crează `src/algorithms/my_algorithm.py` care extinde `TSPAlgorithm`:
   ```python
   from .base import TSPAlgorithm, AlgorithmConfig
   from ..core import AlgorithmResult, TSPProblem, Tour

   class MyAlgorithm(TSPAlgorithm):
       name = "My Algorithm"
       def _solve(self, problem, progress_callback):
           ...
           return AlgorithmResult(...)
   ```
2. Înregistrează-l în `src/algorithms/__init__.py`:
   ```python
   ALGORITHMS["My Algorithm"] = MyAlgorithm
   ```
3. Definește parametrii UI în `src/gui/parameter_panel.py → SCHEMA["My Algorithm"]`.

GUI-ul îl preia automat.

## Testare

```bash
cd tsp-app
pytest tests/
```
