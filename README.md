# Proiect Inteligență Artificială

Proiect final pentru disciplina **Inteligență Artificială** — Universitatea Ștefan cel Mare din Suceava (USV).

Proiectul cuprinde două componente integrate:

1. **`tsp-app/`** — aplicație GUI (PyQt6) pentru **Problema Comis-Voiajorului (TSP)** cu 6 algoritmi, vizualizare live și un **asistent AI (Google Gemini)** pentru analiză de performanță și întrebări în timp real.
2. **`coppeliasim-sim/`** — robot diferențial în **CoppeliaSim** care rezolvă un **labirint** prin **A\*** (planificare clasică) **și prin Reinforcement Learning (Q-learning)** — robotul învață singur ruta.

---

## Structură

```
ProiectIA/
├── tsp-app/                    # Componenta 1 — TSP (PyQt6)
│   ├── src/
│   │   ├── algorithms/         # 6 algoritmi (backtracking, HC, SA, GA, ACO, NN)
│   │   ├── core/               # City, Tour, TSPProblem, AlgorithmResult
│   │   ├── gui/                # Ferestre PyQt6 + theme.py + assistant_panel.py (AI)
│   │   ├── io/                 # Loaders (CSV/JSON/URL) + exporters
│   │   └── llm/                # Integrare Google Gemini (config, client, analist)
│   ├── data/                   # Seturi de date (orașe)
│   ├── llm_config.example.json # Model pentru cheia API (copiază → llm_config.local.json)
│   └── tests/
├── coppeliasim-sim/            # Componenta 2 — robot + labirint
│   ├── src/
│   │   ├── world/grid_map.py   # Discretizare în grid de ocupare
│   │   ├── algorithms/astar.py # A* (planificare clasică)
│   │   ├── controller/         # Controller ZMQ + PathExecutor
│   │   └── rl/                 # Reinforcement Learning (MazeEnv, Q-learning, train, deploy)
│   ├── scenes/Arena.ttt        # Scena labirintului
│   ├── build_map.py            # Generează grila din pereți → scenes/arena_auto.json
│   └── tests/
├── notebooks/                  # Jupyter / Colab — raport comparativ
├── docs/                       # Documentație ([setup.md](docs/setup.md) = ghid instalare)
├── requirements.txt            # Dependențe comune
└── README.md
```

---

## Componenta 1 — Aplicație TSP (`tsp-app/`)

Aplicație PyQt6 care rezolvă TSP prin 6 algoritmi:

| # | Algoritm | Tip | Optimal? |
|---|----------|-----|----------|
| 1 | Backtracking recursiv | Exact | ✅ Da |
| 2 | Hill Climbing | Heuristic local | ❌ Optim local |
| 3 | Simulated Annealing | Stochastic | ⚠️ Probabilistic |
| 4 | Algoritm Genetic | Evolutiv | ⚠️ Probabilistic |
| 5 | Ant Colony Optimization | Bio-inspirat | ⚠️ Probabilistic |
| 6 | Nearest Neighbor | Greedy baseline | ❌ Aproximare rapidă |

**Funcționalități:** selectare algoritm + parametri dinamici, vizualizare live a turului și a convergenței, încărcare date locale (CSV/JSON) sau de pe GitHub, export CSV + grafic.

**🤖 Asistent AI (Google Gemini):** panou lateral pentru întrebări libere despre algoritmi/parametri și buton „Analizează performanța" care trimite rezultatele rulărilor și primește observații + sugestii. Stil vizual cald (gri + portocaliu) centralizat în [`src/gui/theme.py`](tsp-app/src/gui/theme.py). Vezi [tsp-app/README.md](tsp-app/README.md).

---

## Componenta 2 — Robot + labirint (`coppeliasim-sim/`)

Robot diferențial (`Diff_Drive_Bot`) în scena `Arena.ttt` care ajunge de la START la STOP în două moduri:

- **A\*** — planificare optimă pe gridul de ocupare (euristică euclidiană, admisibilă).
- **Reinforcement Learning (Q-learning)** — robotul **învață singur** ruta într-un mediu grid rapid (headless), apoi politica este transferată în CoppeliaSim, unde robotul fizic parcurge drumul.

Comunicare Python ↔ CoppeliaSim prin **ZMQ Remote API**. Vezi [coppeliasim-sim/README.md](coppeliasim-sim/README.md).

---

## Setup rapid

> Ghid detaliat de instalare (Python, CoppeliaSim, VS Code, Git): **[docs/setup.md](docs/setup.md)**.

```bash
git clone https://github.com/mariobucur1/ProiectIA.git
cd ProiectIA
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### Rulează aplicația TSP

```bash
cd tsp-app
python -m src.main
```

Pentru asistentul AI: copiază `llm_config.example.json` → `llm_config.local.json` și pune cheia ta de la [Google AI Studio](https://aistudio.google.com/apikey) (fișierul `.local.json` este în `.gitignore`, nu ajunge în Git).

### Rulează simularea CoppeliaSim

1. Deschide CoppeliaSim și încarcă `coppeliasim-sim/scenes/Arena.ttt`, apoi pornește simularea (▶).
2. Generează harta (o singură dată, cu scena încărcată) și rulează:

```bash
cd coppeliasim-sim
python build_map.py                                   # scenes/arena_auto.json

# Varianta A* (drum determinist)
python -m src.main --goal 0.75 0.23 --map scenes/arena_auto.json --inflate 1

# Varianta Reinforcement Learning
python -m src.rl.train --episodes 2000                # antrenează (headless)
python -m src.rl.deploy --screenshot models/solved_topview.png   # robotul rezolvă labirintul
```

---

## Tehnologii

| Tehnologie | Scop |
|-----------|------|
| Python 3.10+ | Limbaj principal |
| PyQt6 | Interfață grafică TSP |
| NumPy / Matplotlib | Calcule numerice + grafice |
| Google Gemini (REST) | Asistent AI în tsp-app |
| CoppeliaSim + `coppeliasim-zmqremoteapi-client` | Simulator robotic |
| OpenCV | Captură Vision_sensor + detecție waypoints |
| pytest | Teste unitare |

---

## Echipă și licență

Proiect realizat de **Mario Bucur**, **Timu Iustin** și **Marjina Daniela** (USV — disciplina Inteligență Artificială). Detalii în [docs/team.md](docs/team.md).

Cod sursă sub licență MIT (vezi [LICENSE](LICENSE)).
