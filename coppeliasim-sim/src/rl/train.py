"""
Antrenarea agentului Q-learning să rezolve labirintul Arena (headless, rapid).

Rulează mii de episoade într-un mediu grid (MazeEnv), salvează tabelul Q învățat
și o curbă de învățare (recompensă + pași/episod). La final afișează drumul
greedy descoperit, suprapus peste hartă în ASCII.

Rulare:
    cd D:\\ProiectIA\\coppeliasim-sim
    python -m src.rl.train                 # 2000 episoade, parametri impliciți
    python -m src.rl.train --episodes 5000 --alpha 0.3
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .maze_env import MazeEnv
from .qlearning import QLearningAgent, QLearningConfig
from .scene_map import DEFAULT_MAP, load_maze, render_ascii

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
Q_TABLE_PATH = MODELS_DIR / "q_table.npy"
CURVE_PATH = MODELS_DIR / "learning_curve.png"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Antrenare Q-learning pentru labirintul Arena.")
    p.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Cale arena_auto.json.")
    p.add_argument("--episodes", type=int, default=2000, help="Număr de episoade.")
    p.add_argument("--inflate", type=int, default=1, help="Inflatare obstacole (celule).")
    p.add_argument("--max-steps", type=int, default=400, help="Pași maximi per episod.")
    p.add_argument("--alpha", type=float, default=0.2, help="Rata de învățare.")
    p.add_argument("--gamma", type=float, default=0.95, help="Factor de discount.")
    p.add_argument("--epsilon-decay", type=float, default=0.995, help="Decădere ε per episod.")
    p.add_argument("--seed", type=int, default=42, help="Seed reproductibilitate.")
    p.add_argument("--no-plot", action="store_true", help="Nu salva curba de învățare.")
    return p.parse_args()


def train(env: MazeEnv, agent: QLearningAgent, episodes: int):
    """Bucla principală de antrenare. Returnează istoricele pentru grafic."""
    rewards, steps, successes = [], [], []
    for _ in range(episodes):
        state = env.reset()
        total_r, n_steps, done = 0.0, 0, False
        reached = False
        while not done:
            action = agent.select_action(state)
            nxt, r, done, info = env.step(action)
            agent.update(state, action, r, nxt, done and info.get("goal", False))
            state = nxt
            total_r += r
            n_steps += 1
            if info.get("goal"):
                reached = True
        agent.decay_epsilon()
        rewards.append(total_r)
        steps.append(n_steps)
        successes.append(1 if reached else 0)
    return np.array(rewards), np.array(steps), np.array(successes)


def save_curve(rewards, steps, successes, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def smooth(x, w=50):
        if len(x) < w:
            return x
        return np.convolve(x, np.ones(w) / w, mode="valid")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(rewards, color="#D97757", alpha=0.25, label="recompensă/episod")
    axes[0].plot(np.arange(len(smooth(rewards))) + 25, smooth(rewards),
                 color="#D97757", linewidth=2, label="medie mobilă (50)")
    axes[0].set_xlabel("Episod"); axes[0].set_ylabel("Recompensă cumulată")
    axes[0].set_title("Recompensă pe episod"); axes[0].legend(); axes[0].grid(alpha=0.3)

    axes[1].plot(steps, color="#4C7A8C", alpha=0.25, label="pași/episod")
    axes[1].plot(np.arange(len(smooth(steps))) + 25, smooth(steps),
                 color="#4C7A8C", linewidth=2, label="medie mobilă (50)")
    axes[1].set_xlabel("Episod"); axes[1].set_ylabel("Pași până la țintă")
    axes[1].set_title("Lungimea episodului"); axes[1].legend(); axes[1].grid(alpha=0.3)

    fig.suptitle(f"Q-learning — labirint Arena  (rată succes finală: "
                 f"{100 * successes[-100:].mean():.0f}% pe ultimele 100)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    maze = load_maze(args.map, inflate=args.inflate)
    print(f"Hartă: {maze.grid}  start={maze.start}  goal={maze.goal}")

    env = MazeEnv(maze.grid, maze.start, maze.goal, max_steps=args.max_steps)
    cfg = QLearningConfig(alpha=args.alpha, gamma=args.gamma, epsilon_decay=args.epsilon_decay)
    agent = QLearningAgent(env.n_states, env.n_actions, cfg, rng=np.random.default_rng(args.seed))

    print(f"Antrenez {args.episodes} episoade…")
    rewards, steps, successes = train(env, agent, args.episodes)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    agent.save(Q_TABLE_PATH)
    print(f"Tabel Q salvat: {Q_TABLE_PATH}")

    last = slice(-100, None)
    print(f"Rată succes (ultimele 100 ep.): {100 * successes[last].mean():.0f}%")
    print(f"Pași medii (ultimele 100 ep.):  {steps[last].mean():.1f}")

    path = env.greedy_path(agent.policy())
    reached = path[-1] == maze.goal
    print(f"Drum greedy învățat: {len(path)} celule, "
          f"{'ajunge la țintă ✓' if reached else 'NU ajunge la țintă ✗'}")
    print("\n" + render_ascii(maze.grid, maze.start, maze.goal, path))

    if not args.no_plot:
        save_curve(rewards, steps, successes, CURVE_PATH)
        print(f"\nCurbă de învățare: {CURVE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
