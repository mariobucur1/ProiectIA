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
├── coppeliasim-sim/      # Componenta 2: Robot în CoppeliaSim — labirint cu A* + RL
│   ├── src/              # Controller Python + A* + Reinforcement Learning (src/rl/)
│   ├── scenes/           # Scene CoppeliaSim (Arena.ttt)
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
- **🤖 Asistent AI (Google Gemini)** — întrebări libere despre algoritmi/parametri și analiză automată a performanței cu sugestii de îmbunătățire
- Stil vizual cald (gri + portocaliu) centralizat în `src/gui/theme.py`

---

## Componenta 2 — Robot + labirint în CoppeliaSim (`coppeliasim-sim/`)

Robot diferențial (`Diff_Drive_Bot`) în scena **Arena.ttt** care ajunge de la START la STOP în două moduri:

- **A\*** — planificare clasică optimă pe gridul de ocupare.
- **Reinforcement Learning (Q-learning)** — robotul **învață singur** ruta într-un mediu grid rapid (headless), apoi politica e transferată în CoppeliaSim, unde robotul fizic parcurge drumul.

**Componente tehnice:**
- Discretizarea scenei într-un grid de ocupare (generat automat din pereți cu `build_map.py`)
- **A\***: euristică **Distanța Euclidiană** (admisibilă, robotul se rotește liber)
- **RL**: mediu `MazeEnv` (stil Gym) + agent **Q-learning tabular** cu explorare ε-greedy
- Comunicare Python ↔ CoppeliaSim prin **ZMQ Remote API**
- Traducerea drumului în comenzi de viteză diferențială pentru roți (`PathExecutor`)

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

Pentru asistentul AI: copiază `llm_config.example.json` → `llm_config.local.json` și pune cheia de la [Google AI Studio](https://aistudio.google.com/apikey). Fișierul `.local.json` este în `.gitignore` — nu ajunge în Git.

### 5. Rulează simularea CoppeliaSim

1. Deschide CoppeliaSim și încarcă scena `coppeliasim-sim/scenes/Arena.ttt`
2. Pornește simularea (butonul Play)
3. În alt terminal:

```bash
cd coppeliasim-sim
python build_map.py                              # generează harta din pereți

# A* (drum determinist)
python -m src.main --goal 0.75 0.23 --map scenes/arena_auto.json --inflate 1

# Reinforcement Learning (robotul învață singur ruta)
python -m src.rl.train --episodes 2000
python -m src.rl.deploy --screenshot models/solved_topview.png
```

---

## Tehnologii utilizate

| Tehnologie | Scop |
|-----------|------|
| Python 3.10+ | Limbaj principal |
| PyQt6 | Interfață grafică TSP |
| NumPy | Calcule numerice / matrice de distanțe |
| Matplotlib | Grafice de convergență + curbă de învățare RL |
| Google Gemini (REST) | Asistent AI în tsp-app |
| CoppeliaSim | Simulator robotic |
| `coppeliasim-zmqremoteapi-client` | Comunicare Python ↔ CoppeliaSim |
| OpenCV | Captură Vision_sensor + detecție waypoints |
| pytest | Teste unitare |

---

## Echipă

Proiect realizat în echipă (max. 3 studenți) — vezi [docs/team.md](docs/team.md).

---

## Licență

Proiect educațional. Cod sursă disponibil sub licență MIT.
