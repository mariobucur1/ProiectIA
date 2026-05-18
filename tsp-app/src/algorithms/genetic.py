"""
Algoritm Genetic (Evolutiv) pentru TSP.

Componentele:
- **Reprezentare**: permutare de orașe (tur).
- **Selecție**: tournament selection (k = 5).
- **Crossover**: Order Crossover (OX1) — păstrează ordinea relativă.
- **Mutație**: 2-opt swap (reverse segment) cu probabilitatea pm.
- **Elitism**: top E indivizi trec direct în generația următoare.

Avantaj: explorează spațiul soluțiilor în paralel, evită optime locale prin
combinarea materialului genetic de la indivizi diferiți.
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from ..core import AlgorithmResult, TSPProblem, Tour
from .base import ProgressCallback, TSPAlgorithm


class GeneticAlgorithm(TSPAlgorithm):
    """Algoritm genetic cu Order Crossover, mutație 2-opt și elitism."""

    name = "Genetic Algorithm"

    def _solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback],
    ) -> AlgorithmResult:
        rng = np.random.default_rng(self.config.seed)
        ex = self.config.extra

        n = problem.n
        dist = problem.distance_matrix

        population_size = int(ex.get("population_size", 100))
        elite_count = int(ex.get("elite_count", max(2, population_size // 20)))
        tournament_k = int(ex.get("tournament_k", 5))
        crossover_rate = float(ex.get("crossover_rate", 0.9))
        mutation_rate = float(ex.get("mutation_rate", 0.2))
        max_generations = int(ex.get("generations", self.config.max_iterations))

        population = np.array(
            [rng.permutation(n) for _ in range(population_size)], dtype=np.int32
        )
        fitness = np.array([self._tour_length(ind, dist) for ind in population])

        history: list[float] = []
        start_time = time.perf_counter()

        best_idx = int(np.argmin(fitness))
        best_length = float(fitness[best_idx])
        best_individual = population[best_idx].copy()
        history.append(best_length)

        for generation in range(max_generations):
            if self._should_stop(generation, start_time):
                break

            sorted_idx = np.argsort(fitness)
            new_population = np.empty_like(population)
            new_fitness = np.empty_like(fitness)
            new_population[:elite_count] = population[sorted_idx[:elite_count]]
            new_fitness[:elite_count] = fitness[sorted_idx[:elite_count]]

            for k in range(elite_count, population_size):
                p1 = self._tournament_select(rng, fitness, tournament_k)
                p2 = self._tournament_select(rng, fitness, tournament_k)

                if rng.random() < crossover_rate:
                    child = self._order_crossover(population[p1], population[p2], rng)
                else:
                    child = population[p1].copy()

                if rng.random() < mutation_rate:
                    self._mutate_two_opt(child, rng)

                new_population[k] = child
                new_fitness[k] = self._tour_length(child, dist)

            population = new_population
            fitness = new_fitness

            gen_best_idx = int(np.argmin(fitness))
            if fitness[gen_best_idx] < best_length:
                best_length = float(fitness[gen_best_idx])
                best_individual = population[gen_best_idx].copy()

            history.append(best_length)

            if progress_callback and generation % max(1, max_generations // 50) == 0:
                progress_callback(generation, best_length, Tour(best_individual))

        return AlgorithmResult(
            algorithm_name=self.name,
            best_tour=Tour(best_individual),
            best_length=best_length,
            elapsed_seconds=0.0,
            iterations=len(history) - 1,
            convergence_history=history,
            extra={
                "population_size": population_size,
                "elite_count": elite_count,
                "tournament_k": tournament_k,
                "crossover_rate": crossover_rate,
                "mutation_rate": mutation_rate,
            },
        )

    @staticmethod
    def _tour_length(order: np.ndarray, dist: np.ndarray) -> float:
        return float(dist[order, np.roll(order, -1)].sum())

    @staticmethod
    def _tournament_select(
        rng: np.random.Generator, fitness: np.ndarray, k: int
    ) -> int:
        candidates = rng.choice(len(fitness), size=k, replace=False)
        return int(candidates[np.argmin(fitness[candidates])])

    @staticmethod
    def _order_crossover(
        parent1: np.ndarray, parent2: np.ndarray, rng: np.random.Generator
    ) -> np.ndarray:
        """
        Order Crossover (OX1):
        - Copiază un segment continuu din parent1 în child.
        - Completează restul cu orașele din parent2 în ordinea apariției.
        """
        n = len(parent1)
        a, b = sorted(rng.choice(n, size=2, replace=False).tolist())
        child = np.full(n, -1, dtype=np.int32)
        child[a : b + 1] = parent1[a : b + 1]

        in_segment = np.zeros(n, dtype=bool)
        in_segment[parent1[a : b + 1]] = True

        fill_pos = (b + 1) % n
        for city in np.roll(parent2, -(b + 1)):
            if not in_segment[city]:
                child[fill_pos] = city
                fill_pos = (fill_pos + 1) % n
        return child

    @staticmethod
    def _mutate_two_opt(individual: np.ndarray, rng: np.random.Generator) -> None:
        n = len(individual)
        i, j = sorted(rng.choice(n, size=2, replace=False).tolist())
        individual[i : j + 1] = individual[i : j + 1][::-1]
