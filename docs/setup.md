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
- **NumPy** — calcule vectoriale (matrice de distanțe, operații pe tururi)
- **Matplotlib** — grafice de convergență
- **requests** — încărcare seturi de date de pe GitHub
- **coppeliasim-zmqremoteapi-client** — comunicare cu CoppeliaSim
- **scipy** — dilatarea obstacolelor (opțional, dar recomandat)
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

## 5. Visual Studio Code (recomandat)

Pentru editare cod, descarcă [VS Code](https://code.visualstudio.com/) și instalează extensiile:
- **Python** (Microsoft)
- **Pylance**

Apoi: `File → Open Folder → D:\ProiectIA`.

VS Code va detecta automat mediul virtual `.venv` și-l va activa în terminal.

## 6. Git și GitHub

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

## 7. Smoke test (verificare rapidă)

După instalare, testează că totul funcționează:

```powershell
cd D:\ProiectIA\tsp-app
pytest tests/ -v
```

Toate testele trebuie să treacă (✓ verde).

Pentru un test vizual al GUI-ului:
```powershell
python -m src.main
```

Se va deschide fereastra principală. Încarcă `data/simple_5.csv` și rulează Backtracking — ar trebui să găsești optimul în ~1 secundă.
