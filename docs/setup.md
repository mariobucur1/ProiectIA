# Ghid de instalare și configurare

## 1. Python

Instalează Python 3.10+ (recomandat 3.11 sau 3.12) de pe [python.org/downloads](https://www.python.org/downloads/).

La instalare bifează **"Add Python to PATH"**.

Verificare:
```powershell
python --version
# Python 3.11.x sau mai recent
```

## 2. Mediu virtual

Din folderul `D:\ProiectIA`:

```powershell
cd D:\ProiectIA
python -m venv .venv
.venv\Scripts\activate
```

> Prompt-ul ar trebui să afișeze `(.venv)` la început.

## 3. Dependențe

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

Pachete instalate:
- **PyQt6** — GUI pentru TSP
- **NumPy** — calcule vectoriale (matrice de distanțe, operații pe tururi, Q-learning)
- **Matplotlib** — grafice de convergență + curbă de învățare RL
- **requests** — încărcare seturi de date de pe GitHub **și** asistentul AI (Google Gemini, REST)
- **coppeliasim-zmqremoteapi-client** — comunicare cu CoppeliaSim
- **opencv-python** — captură Vision_sensor + detecție waypoints (componenta robot)
- **scipy** — dilatarea obstacolelor (opțional; există fallback NumPy fără el)
- **pytest** + **pytest-qt** — testare

## 4. CoppeliaSim

Descarcă **CoppeliaSim Edu** (versiune educațională, gratuită) de pe [coppeliarobotics.com/downloads](https://www.coppeliarobotics.com/downloads).

La instalare alege calea pe discul D (ex: `D:\CoppeliaSim_Edu`).

ZMQ Remote API este activ automat pe portul **23000** începând cu versiunea 4.5.

### Verificare conexiune ZMQ

Cu CoppeliaSim deschis și o scenă pornită:

```python
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
client = RemoteAPIClient()
sim = client.require("sim")
print("Timp curent simulare:", sim.getSimulationTime())
```

Dacă apare o eroare de conexiune:
- Verifică în log-ul CoppeliaSim: trebuie să apară `ZMQ server started on port 23000`
- Verifică firewall-ul Windows (permite Python prin firewall).

## 5. Cheie API pentru asistentul AI (Google Gemini)

Aplicația TSP are un asistent AI (panoul `🤖 Asistent AI`) bazat pe **Google Gemini**. Cheia se obține gratuit de la [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

Configurarea (cheia **nu** se versionează în Git):

1. Copiază `tsp-app/llm_config.example.json` ca `tsp-app/llm_config.local.json`.
2. Completează:
   ```json
   {
     "api_key": "AIza...",
     "model": "gemini-2.5-flash-lite"
   }
   ```

Alternativ, setează variabila de mediu `GEMINI_API_KEY` (și opțional `GEMINI_MODEL`).

> Modelul `gemini-2.5-flash-lite` funcționează pe nivelul gratuit. Dacă apare eroare `429 / quota`, încearcă alt model gratuit (vezi `GeminiClient.list_models()`). Fără cheie, restul aplicației TSP funcționează normal — doar asistentul e dezactivat.

## 6. Visual Studio Code (recomandat)

Pentru editare cod, descarcă [VS Code](https://code.visualstudio.com/) și instalează extensiile:
- **Python** (Microsoft)
- **Pylance**

Apoi: `File → Open Folder → D:\ProiectIA`.

VS Code va detecta automat mediul virtual `.venv` și-l va activa în terminal.

## 7. Git și GitHub

```powershell
git --version  # verifică instalarea
```

Inițializare repo:
```powershell
cd D:\ProiectIA
git init
git add .
git commit -m "Initial commit: project scaffold"
```

Conectare la GitHub:
```powershell
git remote add origin https://github.com/<user>/ProiectIA.git
git branch -M main
git push -u origin main
```

## 8. Smoke test (verificare rapidă)

După instalare, testează că tot funcționează:

```powershell
cd D:\ProiectIA\tsp-app
pytest tests/ -v

cd D:\ProiectIA\coppeliasim-sim
pytest tests/ -v
```

Toate testele trebuie să treacă (✓ verde).

Pentru un test vizual al GUI-ului TSP:
```powershell
cd D:\ProiectIA\tsp-app
python -m src.main
```

Se va deschide fereastra principală. Încarcă `data/simple_5.csv` și rulează Backtracking — ar trebui să găsești optimul în ~1 secundă.

Pentru componenta robot — antrenarea RL nu necesită CoppeliaSim (rulează headless):
```powershell
cd D:\ProiectIA\coppeliasim-sim
python -m src.rl.train --episodes 2000
```

Ar trebui să afișeze rată de succes 100% și drumul învățat în ASCII. Pentru a vedea robotul real parcurgând labirintul, deschide `scenes/Arena.ttt` în CoppeliaSim, pornește simularea și rulează `python -m src.rl.deploy`.
