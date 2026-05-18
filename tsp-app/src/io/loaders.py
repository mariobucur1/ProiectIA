"""
Loadere pentru seturile de date TSP.

Format CSV așteptat (cu header):
    id,name,x,y
    0,Suceava,26.25,47.64
    1,Iasi,27.59,47.16
    ...

Format JSON așteptat:
    {
      "name": "Romania-10",
      "cities": [
        {"id": 0, "name": "Suceava", "x": 26.25, "y": 47.64},
        ...
      ]
    }

URL GitHub: orice raw URL care servește unul din formatele de mai sus
(detectat automat după extensia .csv / .json).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from urllib.parse import urlparse

from ..core import City, TSPProblem


def load_cities_from_csv(path: str | Path, problem_name: str | None = None) -> TSPProblem:
    """Încarcă orașe dintr-un fișier CSV local."""
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        cities = _parse_csv(f)
    return TSPProblem(cities, name=problem_name or path.stem)


def load_cities_from_json(path: str | Path, problem_name: str | None = None) -> TSPProblem:
    """Încarcă orașe dintr-un fișier JSON local."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    cities = _parse_json(data)
    return TSPProblem(cities, name=problem_name or data.get("name") or path.stem)


def load_cities_from_url(url: str, problem_name: str | None = None, timeout: float = 10.0) -> TSPProblem:
    """
    Încarcă orașe de la un URL (de obicei raw GitHub).

    Formatul (CSV vs JSON) este dedus din extensia URL-ului.
    Pentru GitHub, folosește un raw URL de tipul:
        https://raw.githubusercontent.com/<user>/<repo>/<branch>/path/to/file.csv
    """
    import requests  # import lazy — necesar doar pentru loading remote

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    inferred_name = problem_name or Path(parsed.path).stem or "remote"

    if suffix == ".json":
        data = response.json()
        cities = _parse_json(data)
        return TSPProblem(cities, name=problem_name or data.get("name") or inferred_name)
    if suffix == ".csv" or "text/csv" in response.headers.get("Content-Type", ""):
        cities = _parse_csv(io.StringIO(response.text))
        return TSPProblem(cities, name=inferred_name)

    text = response.text.strip()
    if text.startswith("{") or text.startswith("["):
        data = json.loads(text)
        cities = _parse_json(data)
        return TSPProblem(cities, name=problem_name or inferred_name)
    cities = _parse_csv(io.StringIO(text))
    return TSPProblem(cities, name=inferred_name)


def _parse_csv(stream) -> list[City]:
    text = stream.read() if hasattr(stream, "read") else str(stream)
    if not text.strip():
        raise ValueError("CSV gol.")

    sample = next((ln for ln in text.splitlines() if ln.strip()), "")
    if _row_is_numeric(sample):
        return _parse_csv_headerless(io.StringIO(text))

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV gol sau fără header.")
    lowered = {h.lower() for h in reader.fieldnames}
    required = {"x", "y"}
    if not required.issubset(lowered):
        raise ValueError(
            f"CSV trebuie să conțină coloanele {required} sau să fie headerless "
            f"cu 2-3 coloane numerice. Header găsit: {reader.fieldnames}"
        )

    cities: list[City] = []
    for i, row in enumerate(reader):
        lower = {k.lower(): v for k, v in row.items()}
        city_id = int(lower.get("id", i))
        name = lower.get("name") or f"City_{city_id}"
        cities.append(City(id=city_id, name=name, x=float(lower["x"]), y=float(lower["y"])))
    return cities


def _row_is_numeric(line: str) -> bool:
    """Heuristică: rândul e tratat ca date dacă fiecare câmp e un float valid."""
    fields = [f.strip() for f in line.split(",") if f.strip() != ""]
    if not fields:
        return False
    for f in fields:
        try:
            float(f)
        except ValueError:
            return False
    return True


def _parse_csv_headerless(stream) -> list[City]:
    """
    CSV fără header. Acceptă:
      - 2 coloane: x, y
      - 3 coloane: id, x, y
    Generează nume implicite City_<id>.
    """
    reader = csv.reader(stream)
    cities: list[City] = []
    for i, raw in enumerate(reader):
        fields = [f.strip() for f in raw if f.strip() != ""]
        if not fields:
            continue
        if len(fields) == 2:
            city_id = i
            x, y = float(fields[0]), float(fields[1])
        elif len(fields) >= 3:
            try:
                city_id = int(float(fields[0]))
                x, y = float(fields[1]), float(fields[2])
            except ValueError:
                city_id = i
                x, y = float(fields[0]), float(fields[1])
        else:
            raise ValueError(f"Rând CSV invalid la linia {i + 1}: {raw}")
        cities.append(City(id=city_id, name=f"City_{city_id}", x=x, y=y))
    if not cities:
        raise ValueError("Niciun rând valid în CSV.")
    return cities


def _parse_json(data) -> list[City]:
    if isinstance(data, list):
        raw_cities = data
    elif isinstance(data, dict):
        raw_cities = data.get("cities", [])
    else:
        raise ValueError("JSON invalid pentru TSP.")

    cities: list[City] = []
    for i, item in enumerate(raw_cities):
        city_id = int(item.get("id", i))
        name = item.get("name") or f"City_{city_id}"
        cities.append(City(id=city_id, name=name, x=float(item["x"]), y=float(item["y"])))
    return cities
