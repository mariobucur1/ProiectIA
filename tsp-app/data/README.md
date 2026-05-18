# Seturi de date TSP

| Fișier | Orașe | Format | Descriere |
|--------|------:|--------|-----------|
| `simple_5.csv` | 5 | CSV | Set mic — folosit pentru validare Backtracking (optim exact) |
| `romania_10.csv` | 10 | CSV | Orașe reale din România (coordonate longitudine/latitudine) |
| `random_25.json` | 25 | JSON | 25 orașe aleatorii în pătratul [0,100] |

## Format CSV

```csv
id,name,x,y
0,Suceava,26.250,47.640
...
```

Coloana `id` este opțională (se completează automat dacă lipsește). `name` este de asemenea opțional. Coloanele `x` și `y` sunt obligatorii.

## Format JSON

```json
{
  "name": "NumeSet",
  "cities": [
    {"id": 0, "name": "Suceava", "x": 26.25, "y": 47.64}
  ]
}
```

## Generare seturi proprii

Pentru a genera rapid un set de test în Python:

```python
import json, random
n = 30
cities = [
    {"id": i, "name": f"City_{i}", "x": random.uniform(0, 100), "y": random.uniform(0, 100)}
    for i in range(n)
]
with open(f"random_{n}.json", "w") as f:
    json.dump({"name": f"Random{n}", "cities": cities}, f, indent=2)
```

## Încărcare de pe GitHub

În GUI: **Încarcă de pe GitHub…** → introdu URL raw, de exemplu:

```
https://raw.githubusercontent.com/<user>/ProiectIA/main/tsp-app/data/romania_10.csv
```
