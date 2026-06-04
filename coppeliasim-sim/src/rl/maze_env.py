"""
Mediu grid rapid (stil Gym) pentru antrenarea unui agent RL în labirintul Arena.

Mediul este o discretizare a hărții (GridMap deja inflatată cu raza robotului).
Agentul ocupă o celulă și se mută în 4 direcții. Recompensele încurajează
drumul cel mai scurt până la țintă și penalizează coliziunile cu pereții.

Convenție acțiuni (aliniate cu axele world din CoppeliaSim):
    0 = N  (+row, +y)
    1 = S  (-row, -y)
    2 = E  (+col, +x)
    3 = V  (-col, -x)

Stare = index întreg `row * cols + col` (pentru tabelul Q tabular).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..world import GridCell, GridMap

# (d_row, d_col) pentru fiecare acțiune
ACTION_DELTAS: list[tuple[int, int]] = [(+1, 0), (-1, 0), (0, +1), (0, -1)]
ACTION_NAMES = ["N", "S", "E", "V"]


@dataclass
class RewardConfig:
    """Structura de recompense a mediului."""
    step_penalty: float = -0.05      # cost pe pas — împinge spre drumuri scurte
    collision_penalty: float = -0.75  # lovire perete / ieșire din grid
    goal_reward: float = 10.0         # atingerea țintei


class MazeEnv:
    """Mediu de navigare în labirint pentru Q-learning."""

    def __init__(
        self,
        grid_map: GridMap,
        start: GridCell,
        goal: GridCell,
        max_steps: int = 400,
        reward: RewardConfig | None = None,
    ):
        if not grid_map.is_free(start):
            raise ValueError(f"Celula de start {start} este ocupată/în afara hărții.")
        if not grid_map.is_free(goal):
            raise ValueError(f"Celula țintă {goal} este ocupată/în afara hărții.")
        self.grid = grid_map
        self.start = start
        self.goal = goal
        self.max_steps = max_steps
        self.reward = reward or RewardConfig()

        self.n_actions = len(ACTION_DELTAS)
        self.n_states = grid_map.rows * grid_map.cols

        self._cell = start
        self._steps = 0

    # ── codare stare ──────────────────────────────────────────────────────
    def state_index(self, cell: GridCell) -> int:
        return cell.row * self.grid.cols + cell.col

    def index_to_cell(self, idx: int) -> GridCell:
        return GridCell(idx // self.grid.cols, idx % self.grid.cols)

    # ── API Gym-like ──────────────────────────────────────────────────────
    def reset(self) -> int:
        self._cell = self.start
        self._steps = 0
        return self.state_index(self._cell)

    def step(self, action: int) -> tuple[int, float, bool, dict]:
        """Aplică o acțiune. Returnează (stare_următoare, recompensă, gata, info)."""
        self._steps += 1
        dr, dc = ACTION_DELTAS[action]
        nxt = GridCell(self._cell.row + dr, self._cell.col + dc)

        if not self.grid.is_free(nxt):
            # coliziune: rămâne pe loc, penalizare
            reward = self.reward.collision_penalty
            done = self._steps >= self.max_steps
            return self.state_index(self._cell), reward, done, {"collision": True}

        self._cell = nxt
        if nxt == self.goal:
            return self.state_index(nxt), self.reward.goal_reward, True, {"goal": True}

        truncated = self._steps >= self.max_steps
        return self.state_index(nxt), self.reward.step_penalty, truncated, {}

    @property
    def current_cell(self) -> GridCell:
        return self._cell

    # ── utilitar: extrage drumul greedy dintr-o politică ─────────────────────
    def greedy_path(self, policy, max_len: int = 1000) -> list[GridCell]:
        """
        Urmează acțiunile greedy din `policy` (callable: state_index -> action)
        de la start până la goal. Detectează bucle (oprire de siguranță).
        """
        cell = self.start
        path = [cell]
        seen = set()
        for _ in range(max_len):
            if cell == self.goal:
                break
            s = self.state_index(cell)
            if s in seen:
                break  # buclă — politică incompletă
            seen.add(s)
            dr, dc = ACTION_DELTAS[policy(s)]
            nxt = GridCell(cell.row + dr, cell.col + dc)
            if not self.grid.is_free(nxt):
                break  # politică duce în perete
            cell = nxt
            path.append(cell)
        return path
