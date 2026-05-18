"""Definirea unei instanțe TSP — lista de orașe + matricea de distanțe."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .city import City
from .tour import Tour


class TSPProblem:
    """
    O instanță a problemei Comis-Voiajorului.

    Pre-calculează matricea de distanțe pentru acces O(1) la
    distanța dintre oricare două orașe. Esențial pentru viteza
    algoritmilor (Hill Climbing, ACO etc. interoghează intens această matrice).
    """

    __slots__ = ("cities", "_distance_matrix", "name")

    def __init__(self, cities: Sequence[City], name: str = "Unnamed"):
        if len(cities) < 2:
            raise ValueError("TSP necesită cel puțin 2 orașe.")
        self.cities = tuple(cities)
        self.name = name
        self._distance_matrix = self._compute_distance_matrix()

    @property
    def n(self) -> int:
        """Numărul de orașe."""
        return len(self.cities)

    @property
    def distance_matrix(self) -> np.ndarray:
        """Matricea de distanțe n×n (read-only)."""
        return self._distance_matrix

    def _compute_distance_matrix(self) -> np.ndarray:
        coords = np.array([(c.x, c.y) for c in self.cities], dtype=np.float64)
        diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
        matrix = np.sqrt(np.sum(diff ** 2, axis=-1))
        matrix.setflags(write=False)
        return matrix

    def tour_length(self, tour: Tour) -> float:
        """Calculează lungimea unui tur folosind matricea pre-calculată."""
        return tour.length(self._distance_matrix)

    def city_by_id(self, city_id: int) -> City:
        for c in self.cities:
            if c.id == city_id:
                return c
        raise KeyError(f"Niciun oraș cu id={city_id}.")

    def __repr__(self) -> str:
        return f"TSPProblem(name='{self.name}', n={self.n})"
