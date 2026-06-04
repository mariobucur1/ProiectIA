"""
Agent Q-learning tabular.

Q-learning este un algoritm de RL off-policy care învață funcția de valoare
acțiune-stare Q(s, a) — recompensa cumulativă viitoare așteptată dacă în starea
`s` se alege acțiunea `a` și apoi se urmează politica greedy.

Actualizare (ecuația Bellman, off-policy):
    Q(s,a) ← Q(s,a) + α · [ r + γ · max_a' Q(s',a') − Q(s,a) ]

Explorare: ε-greedy cu ε care scade exponențial (de la mult la puțin),
echilibrând explorarea (acțiuni aleatoare) cu exploatarea (cea mai bună acțiune).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class QLearningConfig:
    """Hiperparametrii agentului."""
    alpha: float = 0.2            # rata de învățare
    gamma: float = 0.95           # factor de discount (cât contează viitorul)
    epsilon_start: float = 1.0    # explorare inițială (100% aleator)
    epsilon_end: float = 0.02     # explorare finală
    epsilon_decay: float = 0.995  # ε ← ε · decay după fiecare episod


class QLearningAgent:
    """Agent tabular Q-learning cu explorare ε-greedy."""

    def __init__(self, n_states: int, n_actions: int, config: QLearningConfig | None = None,
                 rng: np.random.Generator | None = None):
        self.n_states = n_states
        self.n_actions = n_actions
        self.config = config or QLearningConfig()
        self.q = np.zeros((n_states, n_actions), dtype=np.float64)
        self.epsilon = self.config.epsilon_start
        self._rng = rng or np.random.default_rng()

    def select_action(self, state: int, greedy: bool = False) -> int:
        """ε-greedy: aleator cu probabilitate ε, altfel cea mai bună acțiune."""
        if not greedy and self._rng.random() < self.epsilon:
            return int(self._rng.integers(self.n_actions))
        return self.best_action(state)

    def best_action(self, state: int) -> int:
        """Acțiunea greedy (cu departajare aleatoare a egalităților)."""
        row = self.q[state]
        best = np.flatnonzero(row == row.max())
        return int(self._rng.choice(best))

    def update(self, state: int, action: int, reward: float, next_state: int, done: bool) -> None:
        """Un pas de actualizare Bellman."""
        target = reward
        if not done:
            target += self.config.gamma * self.q[next_state].max()
        self.q[state, action] += self.config.alpha * (target - self.q[state, action])

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.config.epsilon_end, self.epsilon * self.config.epsilon_decay)

    def policy(self):
        """Returnează o funcție state_index -> acțiune greedy (pentru extragerea drumului)."""
        return self.best_action

    # ── persistență ──────────────────────────────────────────────────────
    def save(self, path) -> None:
        np.save(path, self.q)

    @classmethod
    def load(cls, path, config: QLearningConfig | None = None) -> "QLearningAgent":
        q = np.load(path)
        agent = cls(q.shape[0], q.shape[1], config)
        agent.q = q
        agent.epsilon = agent.config.epsilon_end
        return agent
