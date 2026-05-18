"""
Algoritm Simulated Annealing (Călirea simulată) pentru TSP.

Inspirat de procesul fizic de călire a metalelor: la temperaturi mari
accepta mișcări proaste pentru a scăpa din optime locale; pe măsură ce
temperatura scade, devine din ce în ce mai "greedy".

Probabilitate de acceptare a unei mutări proaste:
    P(accept) = exp(-ΔE / T)

Operatorul de vecinătate: 2-opt (inversare segment), cu evaluare O(1) a delta.
"""

from __future__ import annotations

import math
import time
from typing import Optional

import numpy as np

from ..core import AlgorithmResult, TSPProblem, Tour
from .base import ProgressCallback, TSPAlgorithm


class SimulatedAnnealingAlgorithm(TSPAlgorithm):
    """Simulated Annealing cu schemă geometrică de răcire."""

    name = "Simulated Annealing"

    def _solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback],
    ) -> AlgorithmResult:
        rng = np.random.default_rng(self.config.seed)
        ex = self.config.extra

        n = problem.n
        dist = problem.distance_matrix

        initial_temp = float(ex.get("initial_temp", self._auto_initial_temp(problem, rng)))
        final_temp = float(ex.get("final_temp", 1e-3))
        cooling_rate = float(ex.get("cooling_rate", 0.995))
        iter_per_temp = int(ex.get("iter_per_temp", max(50, n * 2)))

        tour = Tour(rng.permutation(n))
        current_length = problem.tour_length(tour)
        best_tour = tour.copy()
        best_length = current_length

        history: list[float] = [current_length]
        accepted = 0
        rejected = 0
        total_iterations = 0
        start_time = time.perf_counter()
        temperature = initial_temp

        while temperature > final_temp:
            for _ in range(iter_per_temp):
                if self._should_stop(total_iterations, start_time):
                    break

                i, j = self._random_two_opt(rng, n)
                delta = self._two_opt_delta(tour.order, i, j, dist, n)

                if delta < 0 or rng.random() < math.exp(-delta / temperature):
                    tour.reverse_segment(i, j)
                    current_length += delta
                    accepted += 1
                    if current_length < best_length - 1e-9:
                        best_length = current_length
                        best_tour = tour.copy()
                else:
                    rejected += 1

                total_iterations += 1
                if total_iterations % max(1, iter_per_temp // 4) == 0:
                    history.append(best_length)
                    if progress_callback:
                        progress_callback(total_iterations, best_length, best_tour)

            if self._should_stop(total_iterations, start_time):
                break
            temperature *= cooling_rate

        return AlgorithmResult(
            algorithm_name=self.name,
            best_tour=best_tour,
            best_length=best_length,
            elapsed_seconds=0.0,
            iterations=total_iterations,
            convergence_history=history,
            extra={
                "initial_temp": initial_temp,
                "final_temp": final_temp,
                "cooling_rate": cooling_rate,
                "accepted_moves": accepted,
                "rejected_moves": rejected,
            },
        )

    @staticmethod
    def _auto_initial_temp(problem: TSPProblem, rng: np.random.Generator) -> float:
        """
        Estimează o temperatură inițială care să accepte ~80% din mutările proaste.
        Se bazează pe abaterea standard a costurilor de vecinătate aleatoare.
        """
        n = problem.n
        dist = problem.distance_matrix
        samples = min(100, n * 4)
        deltas: list[float] = []
        order = rng.permutation(n)
        for _ in range(samples):
            i, j = sorted(rng.choice(n, size=2, replace=False).tolist())
            if i == j:
                continue
            a, b = order[i - 1], order[i]
            c, d = order[j], order[(j + 1) % n]
            delta = dist[a, c] + dist[b, d] - dist[a, b] - dist[c, d]
            if delta > 0:
                deltas.append(delta)
        if not deltas:
            return 1.0
        return float(-np.mean(deltas) / math.log(0.8))

    @staticmethod
    def _random_two_opt(rng: np.random.Generator, n: int) -> tuple[int, int]:
        i = int(rng.integers(0, n - 1))
        j = int(rng.integers(i + 1, n))
        return i, j

    @staticmethod
    def _two_opt_delta(
        order: np.ndarray, i: int, j: int, dist: np.ndarray, n: int
    ) -> float:
        a, b = order[i - 1], order[i]
        c, d = order[j], order[(j + 1) % n]
        if i == 0 and j == n - 1:
            return 0.0
        return dist[a, c] + dist[b, d] - dist[a, b] - dist[c, d]
