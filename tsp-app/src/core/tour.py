"""Reprezentarea unui tur (permutare de orașe) în TSP."""

from __future__ import annotations

from typing import Sequence

import numpy as np


class Tour:
    """
    Un tur TSP — permutare a indicilor de orașe.

    Turul se închide automat (ultimul oraș → primul) pentru calculul lungimii.
    Operațiile sunt vectorizate cu NumPy pentru viteză.
    """

    __slots__ = ("_order", "_length", "_dirty")

    def __init__(self, order: Sequence[int]):
        self._order = np.asarray(order, dtype=np.int32)
        self._length: float | None = None
        self._dirty = True

    @property
    def order(self) -> np.ndarray:
        """Vectorul de indici al orașelor în ordinea vizitării."""
        return self._order

    @property
    def size(self) -> int:
        return len(self._order)

    def length(self, distance_matrix: np.ndarray) -> float:
        """
        Lungimea totală a turului (incluzând întoarcerea la primul oraș).

        Returnează rezultatul cache-uit dacă turul nu s-a modificat.
        """
        if not self._dirty and self._length is not None:
            return self._length
        idx = self._order
        nxt = np.roll(idx, -1)
        self._length = float(distance_matrix[idx, nxt].sum())
        self._dirty = False
        return self._length

    def copy(self) -> "Tour":
        new = Tour(self._order.copy())
        new._length = self._length
        new._dirty = self._dirty
        return new

    def swap(self, i: int, j: int) -> None:
        """Schimbă pozițiile i și j (in-place). Invalidează cache-ul."""
        self._order[i], self._order[j] = self._order[j], self._order[i]
        self._dirty = True

    def reverse_segment(self, i: int, j: int) -> None:
        """Inversează segmentul [i..j] (2-opt move, in-place)."""
        if i > j:
            i, j = j, i
        self._order[i:j + 1] = self._order[i:j + 1][::-1]
        self._dirty = True

    def insert(self, src: int, dst: int) -> None:
        """Mută orașul de la poziția src la poziția dst (in-place)."""
        value = self._order[src]
        self._order = np.delete(self._order, src)
        self._order = np.insert(self._order, dst, value)
        self._dirty = True

    def __len__(self) -> int:
        return len(self._order)

    def __iter__(self):
        return iter(self._order)

    def __getitem__(self, idx):
        return self._order[idx]

    def __repr__(self) -> str:
        preview = self._order[:8].tolist()
        suffix = "..." if len(self._order) > 8 else ""
        return f"Tour({preview}{suffix}, size={len(self._order)})"
