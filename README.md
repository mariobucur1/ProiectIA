# Proiect Inteligență Artificială

Proiect final pentru disciplina **Inteligență Artificială** — Universitatea Ștefan cel Mare din Suceava (USV).

Proiectul cuprinde două componente integrate, evaluate ca o lucrare unitară (50% din nota finală — *NP*).

---

## Structură

```
ProiectIA/
├── tsp-app/              # Componenta 1: Aplicație Python GUI pentru Comis-Voiajor (TSP)
│   ├── src/              # Cod sursă (algoritmi, GUI, I/O)
│   ├── data/             # Seturi de date (orașe) — locale + descărcate de pe GitHub
│   ├── tests/            # Teste unitare
│   └── README.md
├── coppeliasim-sim/      # Componenta 2: Simulare CoppeliaSim — Pioneer P3-DX + A*
│   ├── src/              # Controller Python + algoritm A*
│   ├── scenes/           # Scene CoppeliaSim (.ttt)
│   ├── tests/            # Teste pentru pathfinding
│   └── README.md
├── notebooks/            # Jupyter / Google Colab — raport comparativ algoritmi
├── docs/                 # Documentație tehnică, diagrame, prezentare
├── requirements.txt      # Dependențe Python comune
└── README.md             # Acest fișier
```

---

## Componenta 1 — Aplicație TSP (`tsp-app/`)

Aplicație Python cu interfață grafică **PyQt6** care rezolvă **Problema Comis-Voiajorului** prin 6 algoritmi diferiți:

| # | Algoritm | Tip | Optimal? |
|---|----------|-----|----------|
| 1 | Backtracking recursiv | Exact | ✅ Da |
| 2 | Hill Climbing | Heuristic local | ❌ Local optimum |
| 3 | Simulated Annealing | Stochastic | ⚠️ Probabilistic |
| 4 | Algoritm Genetic | Evolutiv | ⚠️ Probabilistic |
| 5 | Ant Colony Optimization | Bio-inspirat (extra) | ⚠️ Probabilistic |
| 6 | Nearest Neighbor | Greedy baseline | ❌ Aproximare rapidă |

**Funcționalități GUI:**
- Selectarea algoritmului din meniu
- Configurarea parametrilor de rulare (popsize, generații, temperatură etc.)
- Vizualizare în timp real a evoluției soluției
- Încărcare date din fișiere **locale** (CSV/JSON) sau de pe **GitHub** (raw URL)
- Export rezultate (CSV + grafic) pentru raportul Colab

---

## Componenta 2 — Simulare CoppeliaSim (`coppeliasim-sim/`)

Simulare a robotului **Pioneer P3-DX** într-un mediu cu obstacole, controlat de un script Python care implementează algoritmul **A\*** pentru navigare optimă spre o țintă.

**Componente tehnice:**
- Discretizarea scenei într-un grid (rețea de celule)
- Reprezentarea hărții ca graf (noduri = celule libere, muchii = tranziții posibile)
- Euristică: **Distanța Euclidiană** (admisibilă, robotul se poate roti liber)
- Comunicare Python ↔ CoppeliaSim prin ZMQ Remote API
- Traducerea drumului A* în comenzi de viteză diferențială pentru roți

---

## Setup rapid

### 1. Clonează repo-ul

```bash
git clone https://github.com/<user>/ProiectIA.git
cd ProiectIA
```

### 2. Creează mediu virtual

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac
```

### 3. Instalează dependențele

```bash
pip install -r requirements.txt
```

### 4. Rulează aplicația TSP

```bash
cd tsp-app
python -m src.main
```

### 5. Rulează simularea CoppeliaSim

1. Deschide CoppeliaSim și încarcă scena `coppeliasim-sim/scenes/pioneer_maze.ttt`
2. Pornește simularea (butonul Play)
3. În alt terminal:

```bash
cd coppeliasim-sim
python -m src.main
```

---

## Tehnologii utilizate

| Tehnologie | Scop |
|-----------|------|
| Python 3.10+ | Limbaj principal |
| PyQt6 | Interfață grafică TSP |
| NumPy | Calcule numerice / matrice de distanțe |
| Matplotlib | Grafice de convergență |
| CoppeliaSim | Simulator robotic |
| `coppeliasim-zmqremoteapi-client` | Comunicare Python ↔ CoppeliaSim |
| pytest | Teste unitare |

---

## Echipă

Proiect realizat în echipă (max. 3 studenți) — vezi [docs/team.md](docs/team.md).

---

## Licență

Proiect educațional. Cod sursă disponibil sub licență MIT.
