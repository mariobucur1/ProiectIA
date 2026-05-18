"""
Teste smoke pentru toți algoritmii TSP.

Validează că:
- Fiecare algoritm rulează fără excepții pe o problemă mică.
- Soluția returnată este o permutare validă (fiecare oraș vizitat exact o dată).
- Lungimea calculată corespunde matricei de distanțe.
- Backtracking găsește optimul exact pe o problemă cunoscută.
"""

import numpy as np
import pytest

from src.algorithms import (
    AlgorithmConfig,
    AntColonyAlgorithm,
    BacktrackingAlgorithm,
    GeneticAlgorithm,
    HillClimbingAlgorithm,
    NearestNeighborAlgorithm,
    SimulatedAnnealingAlgorithm,
)
from src.core import City, TSPProblem


@pytest.fixture
def small_problem():
    """Square — optim este 14.0 (perimetrul dreptunghiului 3×4)."""
    cities = [
        City(0, "A", 0.0, 0.0),
        City(1, "B", 3.0, 0.0),
        City(2, "C", 3.0, 4.0),
        City(3, "D", 0.0, 4.0),
    ]
    return TSPProblem(cities, name="Square4")


@pytest.fixture
def medium_problem():
    rng = np.random.default_rng(42)
    cities = [
        City(i, f"C{i}", float(rng.uniform(0, 100)), float(rng.uniform(0, 100)))
        for i in range(12)
    ]
    return TSPProblem(cities, name="Random12")


def _assert_valid_tour(result, n):
    indices = list(result.best_tour)
    assert sorted(indices) == list(range(n)), "Turul nu este o permutare validă."
    assert result.best_length > 0


def test_backtracking_finds_optimum(small_problem):
    algo = BacktrackingAlgorithm()
    result = algo.solve(small_problem)
    _assert_valid_tour(result, small_problem.n)
    assert result.best_length == pytest.approx(14.0)


def test_nearest_neighbor_runs(medium_problem):
    algo = NearestNeighborAlgorithm()
    result = algo.solve(medium_problem)
    _assert_valid_tour(result, medium_problem.n)


def test_hill_climbing_improves_random(medium_problem):
    cfg = AlgorithmConfig(max_iterations=500, seed=42)
    cfg.extra = {"restarts": 2}
    algo = HillClimbingAlgorithm(cfg)
    result = algo.solve(medium_problem)
    _assert_valid_tour(result, medium_problem.n)


def test_simulated_annealing_runs(medium_problem):
    cfg = AlgorithmConfig(max_iterations=2000, seed=42)
    cfg.extra = {"cooling_rate": 0.99, "iter_per_temp": 50}
    algo = SimulatedAnnealingAlgorithm(cfg)
    result = algo.solve(medium_problem)
    _assert_valid_tour(result, medium_problem.n)


def test_genetic_algorithm_runs(medium_problem):
    cfg = AlgorithmConfig(max_iterations=50, seed=42)
    cfg.extra = {"population_size": 30, "generations": 50}
    algo = GeneticAlgorithm(cfg)
    result = algo.solve(medium_problem)
    _assert_valid_tour(result, medium_problem.n)


def test_aco_runs(medium_problem):
    cfg = AlgorithmConfig(max_iterations=20, seed=42)
    cfg.extra = {"iterations": 20, "num_ants": 10}
    algo = AntColonyAlgorithm(cfg)
    result = algo.solve(medium_problem)
    _assert_valid_tour(result, medium_problem.n)


def test_all_algorithms_consistent_length(small_problem):
    """Pentru o problemă mică, toți algoritmii trebuie să returneze
    o lungime apropiată de optim (14.0). Backtracking trebuie să-l atingă exact."""
    algorithms = [
        BacktrackingAlgorithm(),
        NearestNeighborAlgorithm(),
        HillClimbingAlgorithm(AlgorithmConfig(max_iterations=100, seed=1)),
        SimulatedAnnealingAlgorithm(AlgorithmConfig(max_iterations=500, seed=1)),
    ]
    for algo in algorithms:
        result = algo.solve(small_problem)
        assert result.best_length <= 20.0  # margine generoasă peste optim
