"""
Algoritm Ant Colony Optimization (ACO) pentru TSP.

Bio-inspirat — modelează comportamentul furnicilor:
- Fiecare furnică construiește un tur complet alegând probabilistic
  următorul oraș pe baza feromonului (τ) și a vizibilității (η = 1/distanță).
- După un tur, furnica depune feromon proporțional cu calitatea soluției.
- Feromonul se evaporă în timp (parametrul ρ) pentru a evita convergența prematură.

Probabilitatea de a alege orașul j din i:
    P(i→j) = (τ_ij^α · η_ij^β) / Σ_k (τ_ik^α · η_ik^β)

Implementare: **Ant System** clasic (Dorigo, 1992) — versiunea fundamentală.
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..core import AlgorithmResult, TSPProblem, Tour
from .base import ProgressCallback, TSPAlgorithm


class AntColonyAlgorithm(TSPAlgorithm):
    """Ant Colony System (varianta Ant System) pentru TSP."""

    name = "Ant Colony Optimization"

    def _solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback],
    ) -> AlgorithmResult:
        rng = np.random.default_rng(self.config.seed)
        ex = self.config.extra

        n = problem.n
        dist = problem.distance_matrix

        num_ants = int(ex.get("num_ants", n))
        alpha = float(ex.get("alpha", 1.0))
        beta = float(ex.get("beta", 3.0))
        rho = float(ex.get("evaporation", 0.1))
        Q = float(ex.get("Q", 100.0))
        max_iter = int(ex.get("iterations", self.config.max_iterations))

        with np.errstate(divide="ignore"):
            visibility = 1.0 / dist
        np.fill_diagonal(visibility, 0.0)

        nn_length = self._nearest_neighbor_length(dist, n)
        tau0 = num_ants / max(nn_length, 1e-9)
        pheromone = np.full((n, n), tau0, dtype=np.float64)
        np.fill_diagonal(pheromone, 0.0)

        best_tour: np.ndarray | None = None
        best_length = float("inf")
        history: list[float] = []
        start_time = time.perf_counter()

        for iteration in range(max_iter):
            if self._should_stop(iteration, start_time):
                break

            all_tours = np.empty((num_ants, n), dtype=np.int32)
            all_lengths = np.empty(num_ants, dtype=np.float64)

            for k in range(num_ants):
                tour = self._construct_tour(rng, pheromone, visibility, alpha, beta, n)
                all_tours[k] = tour
                all_lengths[k] = float(dist[tour, np.roll(tour, -1)].sum())

            iter_best_idx = int(np.argmin(all_lengths))
            if all_lengths[iter_best_idx] < best_length:
                best_length = float(all_lengths[iter_best_idx])
                best_tour = all_tours[iter_best_idx].copy()

            pheromone *= 1.0 - rho
            for k in range(num_ants):
                deposit = Q / all_lengths[k]
                t = all_tours[k]
                nxt = np.roll(t, -1)
                pheromone[t, nxt] += deposit
                pheromone[nxt, t] += deposit

            history.append(best_length)
            if progress_callback and iteration % max(1, max_iter // 50) == 0:
                progress_callback(iteration, best_length, Tour(best_tour))

        if best_tour is None:
            best_tour = np.arange(n, dtype=np.int32)
            best_length = float(dist[best_tour, np.roll(best_tour, -1)].sum())

        return AlgorithmResult(
            algorithm_name=self.name,
            best_tour=Tour(best_tour),
            best_length=best_length,
            elapsed_seconds=0.0,
            iterations=len(history),
            convergence_history=history,
            extra={
                "num_ants": num_ants,
                "alpha": alpha,
                "beta": beta,
                "evaporation": rho,
                "Q": Q,
            },
        )

    @staticmethod
    def _construct_tour(
        rng: np.random.Generator,
        pheromone: np.ndarray,
        visibility: np.ndarray,
        alpha: float,
        beta: float,
        n: int,
    ) -> np.ndarray:
        """O furnică construiește un tur complet folosind regula probabilistică."""
        tour = np.empty(n, dtype=np.int32)
        unvisited = np.ones(n, dtype=bool)
        start = int(rng.integers(0, n))
        tour[0] = start
        unvisited[start] = False
        current = start

        for step in range(1, n):
            tau = pheromone[current] ** alpha
            eta = visibility[current] ** beta
            scores = tau * eta
            scores[~unvisited] = 0.0
            total = scores.sum()
            if total <= 0.0:
                choices = np.where(unvisited)[0]
                nxt = int(rng.choice(choices))
            else:
                probs = scores / total
                nxt = int(rng.choice(n, p=probs))
            tour[step] = nxt
            unvisited[nxt] = False
            current = nxt

        return tour

    @staticmethod
    def _nearest_neighbor_length(dist: np.ndarray, n: int) -> float:
        """Lungime NN folosită pentru inițializarea feromonului τ₀."""
        visited = np.zeros(n, dtype=bool)
        visited[0] = True
        current = 0
        total = 0.0
        for _ in range(n - 1):
            row = dist[current].copy()
            row[visited] = np.inf
            nxt = int(np.argmin(row))
            total += float(dist[current, nxt])
            visited[nxt] = True
            current = nxt
        total += float(dist[current, 0])
        return total
