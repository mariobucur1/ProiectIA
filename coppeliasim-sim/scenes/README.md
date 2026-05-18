# Scene CoppeliaSim

## Cum construiești scena `pioneer_maze.ttt`

1. Deschide **CoppeliaSim Edu** (versiune ≥ 4.5).
2. Plasează un robot **Pioneer P3-DX** din *Model browser → robots → mobile → pioneer-p3dx*.
3. Setează poziția robotului la `(−2.0, −2.0, 0.139)` (colțul stânga-jos al hărții).
4. Adaugă **Pure Shapes → Cuboid** pentru fiecare obstacol din `map.json`:
   - Dimensiuni: 0.25m × cell_count × 0.5m înălțime.
   - Coordonatele se calculează cu formula:
     ```
     x = origin_x + (col + 0.5) · cell_size
     y = origin_y + (row + 0.5) · cell_size
     ```
5. Adaugă obstacolele ca obiecte statice (debifează *Dynamic*).
6. Salvează scena ca `pioneer_maze.ttt` în acest folder.

## Activarea ZMQ Remote API

CoppeliaSim ≥ 4.5 are deja API-ul ZMQ activ pe portul **23000**. Verifică:

- Bara de log → la pornire ar trebui să apară `RemoteApi: started ZMQ server on port 23000`
- Dacă nu, încarcă manual plug-in-ul `simExtZMQRemoteApi`

## Verificare rapidă a conexiunii

```python
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
client = RemoteAPIClient()
sim = client.require("sim")
print(sim.getSimulationTime())  # Trebuie să tipărească 0.0 (sau timp curent)
```
