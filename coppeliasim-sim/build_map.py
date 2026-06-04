"""
Construieste grila de ocupare a labirintului Arena.ttt din geometria peretilor.

Citeste live scena din CoppeliaSim (trebuie incarcata Arena.ttt), rasterizeaza
fiecare perete intr-o matrice de ocupare si salveaza scenes/arena_auto.json cu:
  rows, cols, cell_size, origin, obstacles (dreptunghiuri de celule),
  plus metadate: start (world), goal/STOP (world) si waypoint-urile de referinta.

Rezultatul e folosit atat de pipeline-ul A* (src.main) cat si de mediul RL
(src.rl.maze_env) — o singura sursa de adevar pentru harta.

Rulare (cu Arena.ttt incarcata in CoppeliaSim):
    python build_map.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

CELL_SIZE = 0.10                      # m/celula -> arena 2m = 20x20
ORIGIN = (-1.0, -1.0)                 # coltul (row=0,col=0) in world
ROWS = COLS = 20

OUT = Path(__file__).resolve().parent / "scenes" / "arena_auto.json"

# Pozitii world ale waypoint-urilor de referinta (extrase din Vision_sensor).
WAYPOINTS = {
    "START": (-0.75, -0.75), "A": (0.75, -0.75), "B": (0.75, -0.25),
    "C": (-0.75, -0.25), "D": (-0.75, 0.75), "E": (-0.25, 0.75),
    "F": (-0.25, 0.25), "G": (0.25, 0.25), "H": (0.25, 0.75),
    "I": (0.75, 0.75), "STOP": (0.75, 0.23),
}


def _fp(sim, h, param) -> float:
    v = sim.getObjectFloatParam(h, param)
    return float(v[-1]) if isinstance(v, (list, tuple)) else float(v)


def wall_rect_world(sim, h) -> tuple[float, float, float, float]:
    """Bounding box world-aligned (x_min, y_min, x_max, y_max) al unui perete."""
    pos = sim.getObjectPosition(h, -1)
    ori = sim.getObjectOrientation(h, -1)
    xl = _fp(sim, h, sim.objfloatparam_objbbox_min_x)
    Xl = _fp(sim, h, sim.objfloatparam_objbbox_max_x)
    yl = _fp(sim, h, sim.objfloatparam_objbbox_min_y)
    Yl = _fp(sim, h, sim.objfloatparam_objbbox_max_y)
    sx, sy = Xl - xl, Yl - yl
    ct, st = abs(math.cos(ori[2])), abs(math.sin(ori[2]))
    wx = sx * ct + sy * st
    wy = sx * st + sy * ct
    return (pos[0] - wx / 2, pos[1] - wy / 2, pos[0] + wx / 2, pos[1] + wy / 2)


def world_rect_to_cells(x_min, y_min, x_max, y_max) -> tuple[int, int, int, int]:
    """Convertste un dreptunghi world in indici de celule (r1, c1, r2, c2), clamp-uit."""
    c1 = int(math.floor((x_min - ORIGIN[0]) / CELL_SIZE))
    c2 = int(math.floor((x_max - ORIGIN[0]) / CELL_SIZE))
    r1 = int(math.floor((y_min - ORIGIN[1]) / CELL_SIZE))
    r2 = int(math.floor((y_max - ORIGIN[1]) / CELL_SIZE))
    clamp = lambda v, hi: max(0, min(hi - 1, v))
    return clamp(r1, ROWS), clamp(c1, COLS), clamp(r2, ROWS), clamp(c2, COLS)


def main() -> None:
    sim = RemoteAPIClient("127.0.0.1", 23000).require("sim")

    obstacles = []
    for i in range(1, 10):
        h = sim.getObject(f"/Arena_Wall_{i}")
        rect = wall_rect_world(sim, h)
        obstacles.append(list(world_rect_to_cells(*rect)))

    data = {
        "name": "Arena (maze)",
        "rows": ROWS,
        "cols": COLS,
        "cell_size": CELL_SIZE,
        "origin": list(ORIGIN),
        "obstacles": obstacles,
        "start_world": list(WAYPOINTS["START"]),
        "goal_world": list(WAYPOINTS["STOP"]),
        "waypoints_world": WAYPOINTS,
    }
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Scris: {OUT}  ({ROWS}x{COLS} @ {CELL_SIZE}m, {len(obstacles)} pereti)")


if __name__ == "__main__":
    main()
