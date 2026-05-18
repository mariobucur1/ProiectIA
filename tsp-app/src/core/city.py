"""Reprezentarea unui oraș în problema TSP."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True, slots=True)
class City:
    """Un oraș identificat prin nume și coordonate 2D."""

    id: int
    name: str
    x: float
    y: float

    def distance_to(self, other: "City") -> float:
        """Distanța euclidiană până la alt oraș."""
        return hypot(self.x - other.x, self.y - other.y)

    def __repr__(self) -> str:
        return f"City({self.id}, '{self.name}', {self.x:.2f}, {self.y:.2f})"
