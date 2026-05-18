"""Rezultatul standardizat returnat de orice algoritm TSP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tour import Tour


@dataclass
class AlgorithmResult:
    """
    Rezultatul unei rulări de algoritm.

    Conține turul final, lungimea, istoricul de convergență (pentru grafice)
    și statistici de execuție (timp, iterații).
    """

    algorithm_name: str
    best_tour: Tour
    best_length: float
    elapsed_seconds: float
    iterations: int
    convergence_history: list[float] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializare pentru export CSV / JSON / raport Colab."""
        return {
            "algorithm": self.algorithm_name,
            "best_length": self.best_length,
            "elapsed_seconds": self.elapsed_seconds,
            "iterations": self.iterations,
            "tour_size": len(self.best_tour),
            **{f"extra_{k}": v for k, v in self.extra.items()},
        }

    def __repr__(self) -> str:
        return (
            f"AlgorithmResult({self.algorithm_name}, "
            f"length={self.best_length:.2f}, time={self.elapsed_seconds:.3f}s, "
            f"iter={self.iterations})"
        )
