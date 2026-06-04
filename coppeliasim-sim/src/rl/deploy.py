"""
Transferă politica Q-learning învățată în CoppeliaSim și conduce robotul real.

Pipeline:
1. Încarcă harta (arena_auto.json) + tabelul Q antrenat (models/q_table.npy).
2. Extrage drumul greedy de celule de la START la STOP.
3. Colapsează celulele coliniare în colțuri → listă scurtă de waypoints.
4. Convertește colțurile în coordonate world și le dă lui PathExecutor,
   care comandă robotul Diff_Drive_Bot prin ZMQ Remote API.

Rulare (cu Arena.ttt încărcată + simulare gata de pornit în CoppeliaSim):
    cd D:\\ProiectIA\\coppeliasim-sim
    python -m src.rl.deploy                 # antrenează implicit dacă lipsește tabelul Q
    python -m src.rl.deploy --dry-run       # doar afișează waypoints, fără robot
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..controller import PathExecutor, PioneerController
from ..world import GridCell
from .maze_env import MazeEnv
from .qlearning import QLearningAgent
from .scene_map import DEFAULT_MAP, load_maze, render_ascii
from .train import Q_TABLE_PATH


def collapse_collinear(path: list[GridCell]) -> list[GridCell]:
    """Păstrează doar colțurile (punctele unde se schimbă direcția)."""
    if len(path) <= 2:
        return list(path)
    corners = [path[0]]
    for prev, cur, nxt in zip(path, path[1:], path[2:]):
        d1 = (cur.row - prev.row, cur.col - prev.col)
        d2 = (nxt.row - cur.row, nxt.col - cur.col)
        if d1 != d2:
            corners.append(cur)
    corners.append(path[-1])
    return corners


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Deploy politică Q-learning în CoppeliaSim.")
    p.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Cale arena_auto.json.")
    p.add_argument("--q-table", type=Path, default=Q_TABLE_PATH, help="Cale tabel Q (.npy).")
    p.add_argument("--inflate", type=int, default=1, help="Inflatare obstacole (celule).")
    p.add_argument("--host", default="localhost", help="IP CoppeliaSim ZMQ.")
    p.add_argument("--port", type=int, default=23000, help="Port CoppeliaSim ZMQ.")
    p.add_argument("--dry-run", action="store_true", help="Doar afișează drumul, fără robot.")
    p.add_argument("--screenshot", type=Path, default=None,
                   help="Salvează o captură de sus (Vision_sensor) la final.")
    return p.parse_args()


def capture_top_view(sim, out_path: Path) -> None:
    """Salvează imaginea curentă din /Vision_sensor (vedere de sus) pe disc."""
    import numpy as np
    try:
        import cv2
    except ImportError:
        print("cv2 lipsește — sar peste screenshot.")
        return
    vs = sim.getObject("/Vision_sensor")
    result = sim.getVisionSensorImg(vs)  # senzorul randează automat, fără handle explicit
    if len(result) == 2:
        img_bytes, res = result
        w, h = int(res[0]), int(res[1])
    else:
        img_bytes, w, h = result[0], int(result[1]), int(result[2])
    img = np.frombuffer(img_bytes, dtype=np.uint8).reshape(h, w, 3)
    img = np.flipud(img).copy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    print(f"Captură salvată: {out_path}")


def main() -> int:
    args = parse_args()
    maze = load_maze(args.map, inflate=args.inflate)
    env = MazeEnv(maze.grid, maze.start, maze.goal)

    if not args.q_table.exists():
        print(f"Tabelul Q lipsește ({args.q_table}). Rulează întâi: python -m src.rl.train")
        return 1
    agent = QLearningAgent.load(args.q_table)
    if agent.q.shape[0] != env.n_states:
        print("Tabelul Q nu se potrivește cu harta curentă. Re-antrenează.")
        return 1

    path = env.greedy_path(agent.policy())
    if path[-1] != maze.goal:
        print("Politica învățată NU ajunge la țintă. Re-antrenează cu mai multe episoade.")
        print("\n" + render_ascii(maze.grid, maze.start, maze.goal, path))
        return 2

    corners = collapse_collinear(path)
    waypoints = [maze.grid_to_world(c) for c in corners]
    print(f"Drum: {len(path)} celule → {len(corners)} colțuri (waypoints).")
    print("\n" + render_ascii(maze.grid, maze.start, maze.goal, path))
    print("\nWaypoints world (x, y):")
    for i, (x, y) in enumerate(waypoints):
        print(f"  {i:2d}: ({x:+.2f}, {y:+.2f})")

    if args.dry_run:
        print("\n[dry-run] Nu trimit comenzi robotului.")
        return 0

    controller = PioneerController(host=args.host, port=args.port)
    print(f"\nConectare la CoppeliaSim {args.host}:{args.port}…")
    controller.connect()
    controller.start_simulation()
    try:
        x, y, _ = controller.get_pose()
        print(f"Pornire robot din world=({x:+.2f}, {y:+.2f}). Urmez {len(waypoints)} waypoints…")
        executor = PathExecutor(controller)
        # sărim primul waypoint (= celula de start, robotul e deja acolo)
        success = executor.follow(waypoints[1:])
        print("Țintă atinsă ✓ — robotul a rezolvat labirintul!" if success
              else "Timeout — robotul nu a ajuns la țintă.")
        if args.screenshot is not None:
            controller.stop()
            capture_top_view(controller.sim, args.screenshot)
        return 0 if success else 2
    finally:
        controller.stop()
        controller.stop_simulation()
        controller.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
