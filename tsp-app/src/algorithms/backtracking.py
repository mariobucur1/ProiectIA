"""
Algoritm Backtracking recursiv pentru TSP.

Soluție exactă — explorează toate permutările cu pruning prin
branch-and-bound (renunță la ramuri care depășesc deja cel mai bun cost cunoscut).

Complexitate: O(n!) în cel mai rău caz. Practic, pruning-ul reduce
mult timpul, dar algoritmul rămâne folosibil doar pentru n ≤ ~12.
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..core import AlgorithmResult, TSPProblem, Tour
from .base import AlgorithmConfig, ProgressCallback, TSPAlgorithm


class BacktrackingAlgorithm(TSPAlgorithm):
    """Backtracking cu branch-and-bound."""

    name = "Backtracking"

    def _solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback],
    ) -> AlgorithmResult:
        n = problem.n
        dist = problem.distance_matrix

        if n > 13 and not self.config.extra.get("force", False):
            raise ValueError(
                f"Backtracking este impracticabil pentru n={n} (limită ~13). "
                "Setează config.extra['force']=True pentru a încerca oricum."
            )

        best_length = float("inf")
        best_path: np.ndarray | None = None
        visited = np.zeros(n, dtype=bool)
        current_path = np.zeros(n, dtype=np.int32)
        nodes_explored = 0
        history: list[float] = []
        start_time = time.perf_counter()

        def recurse(depth: int, current_length: float) -> None:
            nonlocal best_length, best_path, nodes_explored

            if self.config.time_limit_seconds is not None:
                if (time.perf_counter() - start_time) >= self.config.time_limit_seconds:
                    return

            nodes_explored += 1

            if depth == n:
                total = current_length + dist[current_path[-1], current_path[0]]
                if total < best_length:
                    best_length = total
                    best_path = current_path.copy()
                    history.append(best_length)
                    if progress_callback:
                        progress_callback(nodes_explored, best_length, Tour(best_path))
                return

            last = current_path[depth - 1]
            for city in range(n):
                if visited[city]:
                    continue
                new_length = current_length + dist[last, city]
                if new_length >= best_length:
                    continue
                visited[city] = True
                current_path[depth] = city
                recurse(depth + 1, new_length)
                visited[city] = False

        visited[0] = True
        current_path[0] = 0
        recurse(1, 0.0)

        if best_path is None:
            best_path = np.arange(n, dtype=np.int32)
            best_length = problem.tour_length(Tour(best_path))

        return AlgorithmResult(
            algorithm_name=self.name,
            best_tour=Tour(best_path),
            best_length=best_length,
            elapsed_seconds=0.0,
            iterations=nodes_explored,
            convergence_history=history,
            extra={"nodes_explored": nodes_explored},
        )
