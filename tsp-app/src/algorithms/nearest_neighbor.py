"""
Algoritm Nearest Neighbor (greedy) pentru TSP.

La fiecare pas alege orașul nevizitat cel mai apropiat. Foarte rapid (O(n²))
dar de obicei produce soluții cu ~25% mai lungi decât optimul. Util ca:
- soluție inițială pentru Hill Climbing / Simulated Annealing
- baseline de comparație în raportul de performanță
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ..core import AlgorithmResult, TSPProblem, Tour
from .base import ProgressCallback, TSPAlgorithm


class NearestNeighborAlgorithm(TSPAlgorithm):
    """Construire greedy: pornește dintr-un oraș, alege mereu cel mai apropiat."""

    name = "Nearest Neighbor"

    def _solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback],
    ) -> AlgorithmResult:
        n = problem.n
        dist = problem.distance_matrix
        start_city = int(self.config.extra.get("start_city", 0))

        visited = np.zeros(n, dtype=bool)
        path = np.zeros(n, dtype=np.int32)
        visited[start_city] = True
        path[0] = start_city
        current = start_city

        for step in range(1, n):
            row = dist[current].copy()
            row[visited] = np.inf
            nxt = int(np.argmin(row))
            path[step] = nxt
            visited[nxt] = True
            current = nxt

            if progress_callback and step % max(1, n // 20) == 0:
                progress_callback(step, problem.tour_length(Tour(path[: step + 1])), Tour(path))

        tour = Tour(path)
        length = problem.tour_length(tour)

        return AlgorithmResult(
            algorithm_name=self.name,
            best_tour=tour,
            best_length=length,
            elapsed_seconds=0.0,
            iterations=n,
            convergence_history=[length],
            extra={"start_city": start_city},
        )
