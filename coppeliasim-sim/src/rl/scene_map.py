"""
Helper comun pentru încărcarea labirintului din scenes/arena_auto.json.

Atât antrenarea (train.py) cât și deploy-ul (deploy.py) au nevoie de aceeași
hartă, celule de start/goal și conversii grid↔world — definite o singură dată aici.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..world import GridCell, GridMap

DEFAULT_MAP = Path(__file__).resolve().parents[2] / "scenes" / "arena_auto.json"


@dataclass
class Maze:
    """Harta labirintului + punctele cheie, gata pentru RL și pentru execuție."""
    grid: GridMap
    start: GridCell
    goal: GridCell
    data: dict

    def grid_to_world(self, cell: GridCell) -> tuple[float, float]:
        return self.grid.grid_to_world(cell)


def load_maze(json_path: Path | str = DEFAULT_MAP, inflate: int = 1) -> Maze:
    """
    Încarcă harta din JSON, opțional inflatează obstacolele (raza robotului)
    și calculează celulele de start/goal din coordonatele world salvate.
    """
    json_path = Path(json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))

    grid = GridMap(
        rows=int(data["rows"]),
        cols=int(data["cols"]),
        cell_size=float(data["cell_size"]),
        origin=tuple(data["origin"]),
    )
    for r1, c1, r2, c2 in data.get("obstacles", []):
        grid.add_rectangle_obstacle(GridCell(r1, c1), GridCell(r2, c2))
    if inflate > 0:
        grid.inflate_obstacles(inflate)

    start = grid.world_to_grid(*data["start_world"])
    goal = grid.world_to_grid(*data["goal_world"])
    return Maze(grid=grid, start=start, goal=goal, data=data)


def render_ascii(grid: GridMap, start: GridCell, goal: GridCell,
                 path: list[GridCell] | None = None) -> str:
    """ASCII al hărții: '#'=perete, 'S'=start, 'X'=goal, '*'=drum, '.'=liber."""
    path_set = set((c.row, c.col) for c in (path or []))
    lines = []
    for r in range(grid.rows - 1, -1, -1):
        row = []
        for c in range(grid.cols):
            if (r, c) == (start.row, start.col):
                row.append("S")
            elif (r, c) == (goal.row, goal.col):
                row.append("X")
            elif grid.occupancy[r, c]:
                row.append("#")
            elif (r, c) in path_set:
                row.append("*")
            else:
                row.append(".")
        lines.append(" ".join(row))
    return "\n".join(lines)
