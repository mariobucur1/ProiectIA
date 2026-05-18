"""
Algoritm Hill Climbing pentru TSP.

Strategia "alpinistului" — pornește de la o soluție inițială (random sau NN)
și încearcă iterativ să o îmbunătățească prin mutări locale (2-opt swap).
Se oprește când nu mai există îmbunătățiri (optim local).

Variante implementate:
- "first_improvement": prima vecinătate îmbunătățitoare
- "best_improvement": cea mai bună vecinătate (mai lent, dar mai bun pe iterație)
- "random_restart": restart-uri multiple pentru a scăpa de optime locale
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..core import AlgorithmResult, TSPProblem, Tour
from .base import ProgressCallback, TSPAlgorithm
from .nearest_neighbor import NearestNeighborAlgorithm


class HillClimbingAlgorithm(TSPAlgorithm):
    """Hill Climbing cu 2-opt (best/first improvement) și random restart."""

    name = "Hill Climbing"

    def _solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback],
    ) -> AlgorithmResult:
        rng = np.random.default_rng(self.config.seed)
        strategy = self.config.extra.get("strategy", "best_improvement")
        num_restarts = int(self.config.extra.get("restarts", 1))
        use_nn_start = bool(self.config.extra.get("nn_start", True))

        n = problem.n
        dist = problem.distance_matrix
        start_time = time.perf_counter()

        best_overall_tour: Tour | None = None
        best_overall_length = float("inf")
        history: list[float] = []
        total_iterations = 0

        for restart in range(num_restarts):
            if use_nn_start and restart == 0:
                nn_config = self.config.__class__()
                nn_config.extra = {"start_city": 0}
                tour = NearestNeighborAlgorithm(nn_config).solve(problem).best_tour
            else:
                tour = Tour(rng.permutation(n))

            current_length = problem.tour_length(tour)

            improved = True
            while improved:
                if self._should_stop(total_iterations, start_time):
                    break
                improved = False
                best_delta = 0.0
                best_move: tuple[int, int] | None = None

                for i in range(n - 1):
                    for j in range(i + 1, n):
                        delta = self._two_opt_delta(tour.order, i, j, dist, n)
                        if delta < best_delta - 1e-12:
                            best_delta = delta
                            best_move = (i, j)
                            if strategy == "first_improvement":
                                break
                    if strategy == "first_improvement" and best_move is not None:
                        break

                if best_move is not None:
                    i, j = best_move
                    tour.reverse_segment(i, j)
                    current_length += best_delta
                    improved = True
                    total_iterations += 1
                    history.append(current_length)
                    if progress_callback and total_iterations % 5 == 0:
                        progress_callback(total_iterations, current_length, tour)

            if current_length < best_overall_length:
                best_overall_length = current_length
                best_overall_tour = tour.copy()

            if self._should_stop(total_iterations, start_time):
                break

        if best_overall_tour is None:
            best_overall_tour = Tour(rng.permutation(n))
            best_overall_length = problem.tour_length(best_overall_tour)

        return AlgorithmResult(
            algorithm_name=self.name,
            best_tour=best_overall_tour,
            best_length=best_overall_length,
            elapsed_seconds=0.0,
            iterations=total_iterations,
            convergence_history=history,
            extra={"strategy": strategy, "restarts": num_restarts},
        )

    @staticmethod
    def _two_opt_delta(
        order: np.ndarray, i: int, j: int, dist: np.ndarray, n: int
    ) -> float:
        """
        Schimbarea de cost dacă inversăm segmentul [i..j].

        Calcul O(1): doar muchiile la limitele segmentului se schimbă.
        """
        a, b = order[i - 1], order[i]
        c, d = order[j], order[(j + 1) % n]
        if i == 0 and j == n - 1:
            return 0.0
        return dist[a, c] + dist[b, d] - dist[a, b] - dist[c, d]
