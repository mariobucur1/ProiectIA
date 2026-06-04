

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .algorithms import AStarPathfinder, NoPathFoundError
from .controller import PathExecutor, PioneerController
from .world import GridCell, GridMap


def build_default_map() -> GridMap:
    """Hartă de exemplu — un labirint mic de 20×20 celule de 0.25m."""
    gm = GridMap(rows=20, cols=20, cell_size=0.25, origin=(-2.5, -2.5))
    gm.add_rectangle_obstacle(GridCell(5, 3), GridCell(5, 12))
    gm.add_rectangle_obstacle(GridCell(10, 8), GridCell(15, 8))
    gm.add_rectangle_obstacle(GridCell(13, 2), GridCell(13, 14))
    return gm


def load_map_from_json(path: Path) -> GridMap:

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    gm = GridMap(
        rows=int(data["rows"]),
        cols=int(data["cols"]),
        cell_size=float(data.get("cell_size", 0.25)),
        origin=tuple(data.get("origin", (0.0, 0.0))),
    )
    for rect in data.get("obstacles", []):
        r1, c1, r2, c2 = rect
        gm.add_rectangle_obstacle(GridCell(r1, c1), GridCell(r2, c2))
    return gm


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Navigare Pioneer P3-DX cu A*.")
    p.add_argument("--goal", nargs=2, type=float, required=True, metavar=("X", "Y"),
                   help="Coordonatele țintei în metri (world).")
    p.add_argument("--map", type=Path, default=None,
                   help="Cale către fișier JSON cu harta (opțional).")
    p.add_argument("--host", default="localhost", help="IP CoppeliaSim ZMQ.")
    p.add_argument("--port", type=int, default=23000, help="Port CoppeliaSim ZMQ.")
    p.add_argument("--inflate", type=int, default=1,
                   help="Raport de siguranță (celule) pentru obstacole.")
    p.add_argument("--no-smooth", action="store_true",
                   help="Dezactivează smoothing-ul drumului A*.")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    grid_map = load_map_from_json(args.map) if args.map else build_default_map()
    if args.inflate > 0:
        try:
            grid_map.inflate_obstacles(args.inflate)
        except ImportError:
            print("Avertisment: scipy lipsește, dezactivez inflate.", file=sys.stderr)
    print(f"Hartă: {grid_map}")

    pathfinder = AStarPathfinder(grid_map)
    controller = PioneerController(host=args.host, port=args.port)

    print(f"Conectare la CoppeliaSim {args.host}:{args.port}…")
    controller.connect()
    controller.start_simulation()

    try:
        x, y, _ = controller.get_pose()
        start_cell = grid_map.world_to_grid(x, y)
        goal_cell = grid_map.world_to_grid(*args.goal)
        print(f"Start: world=({x:.2f}, {y:.2f}) → {start_cell}")
        print(f"Țintă: world={tuple(args.goal)} → {goal_cell}")

        try:
            cells = pathfinder.find_path(start_cell, goal_cell)
        except NoPathFoundError as exc:
            print(f"Nu pot ajunge la țintă: {exc}", file=sys.stderr)
            return 1

        if not args.no_smooth:
            cells = AStarPathfinder.smooth_path(cells, grid_map)
        waypoints = [grid_map.grid_to_world(c) for c in cells]
        print(f"Drum găsit: {len(waypoints)} waypoints, "
              f"{(len(cells) - 1) * grid_map.cell_size:.2f}m estimat.")

        executor = PathExecutor(controller)
        success = executor.follow(waypoints)
        print("Țintă atinsă ✓" if success else "Timeout — robotul nu a ajuns la țintă.")
        return 0 if success else 2
    finally:
        controller.stop()
        controller.stop_simulation()
        controller.disconnect()


if __name__ == "__main__":
    sys.exit(main())
