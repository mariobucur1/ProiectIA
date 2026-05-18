"""Algoritmi pentru rezolvarea problemei TSP."""

from .base import TSPAlgorithm, AlgorithmConfig
from .backtracking import BacktrackingAlgorithm
from .hill_climbing import HillClimbingAlgorithm
from .simulated_annealing import SimulatedAnnealingAlgorithm
from .genetic import GeneticAlgorithm
from .aco import AntColonyAlgorithm
from .nearest_neighbor import NearestNeighborAlgorithm

ALGORITHMS = {
    "Backtracking": BacktrackingAlgorithm,
    "Hill Climbing": HillClimbingAlgorithm,
    "Simulated Annealing": SimulatedAnnealingAlgorithm,
    "Genetic Algorithm": GeneticAlgorithm,
    "Ant Colony Optimization": AntColonyAlgorithm,
    "Nearest Neighbor": NearestNeighborAlgorithm,
}

__all__ = [
    "TSPAlgorithm",
    "AlgorithmConfig",
    "ALGORITHMS",
    "BacktrackingAlgorithm",
    "HillClimbingAlgorithm",
    "SimulatedAnnealingAlgorithm",
    "GeneticAlgorithm",
    "AntColonyAlgorithm",
    "NearestNeighborAlgorithm",
]
