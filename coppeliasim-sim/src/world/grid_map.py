"""
Discretizarea mediului CoppeliaSim într-un grid 2D pentru A*.

Convenție:
- Coordonate **world** (CoppeliaSim): metri, axe X/Y, originea în (0,0).
- Coordonate **grid**: indici (row, col) cu (0,0) în colțul stânga-jos.
- Fiecare celulă reprezintă un pătrat de `cell_size` metri × `cell_size` metri.
- O celulă este liberă (True) sau obstacol (False).

Conversia world ↔ grid se face prin metodele `world_to_grid()` și `grid_to_world()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True, slots=True)
class GridCell:
    """Coordonate de celulă în grid."""
    row: int
    col: int

    def __iter__(self):
        yield self.row
        yield self.col


class GridMap:
    """
    Reprezentare 2D a mediului de simulare.

    Atribute:
        rows, cols: dimensiunile grid-ului
        cell_size: dimensiunea unei celule în metri
        origin: coordonatele world ale colțului (0,0) din grid
        occupancy: matrice booleană — True = obstacol, False = liber
    """

    __slots__ = ("rows", "cols", "cell_size", "origin", "_occupancy")

    def __init__(
        self,
        rows: int,
        cols: int,
        cell_size: float = 0.25,
        origin: tuple[float, float] = (0.0, 0.0),
    ):
        if rows <= 0 or cols <= 0:
            raise ValueError("rows și cols trebuie să fie pozitive.")
        if cell_size <= 0:
            raise ValueError("cell_size trebuie să fie pozitiv.")
        self.rows = rows
        self.cols = cols
        self.cell_size = float(cell_size)
        self.origin = origin
        self._occupancy = np.zeros((rows, cols), dtype=bool)

    @property
    def occupancy(self) -> np.ndarray:
        return self._occupancy

    def is_inside(self, cell: GridCell) -> bool:
        return 0 <= cell.row < self.rows and 0 <= cell.col < self.cols

    def is_free(self, cell: GridCell) -> bool:
        return self.is_inside(cell) and not self._occupancy[cell.row, cell.col]

    def set_obstacle(self, cell: GridCell, value: bool = True) -> None:
        if not self.is_inside(cell):
            raise IndexError(f"Celula {cell} este în afara grid-ului.")
        self._occupancy[cell.row, cell.col] = value

    def add_rectangle_obstacle(
        self, top_left: GridCell, bottom_right: GridCell
    ) -> None:
        """Marchează un dreptunghi de celule ca obstacole."""
        r1, c1 = top_left.row, top_left.col
        r2, c2 = bottom_right.row, bottom_right.col
        r1, r2 = sorted((r1, r2))
        c1, c2 = sorted((c1, c2))
        self._occupancy[r1 : r2 + 1, c1 : c2 + 1] = True

    def world_to_grid(self, x: float, y: float) -> GridCell:
        """Convertește coordonate world în indici de celulă."""
        col = int((x - self.origin[0]) / self.cell_size)
        row = int((y - self.origin[1]) / self.cell_size)
        return GridCell(row=row, col=col)

    def grid_to_world(self, cell: GridCell) -> tuple[float, float]:
        """Convertește indici de celulă în coordonate world (centrul celulei)."""
        x = self.origin[0] + (cell.col + 0.5) * self.cell_size
        y = self.origin[1] + (cell.row + 0.5) * self.cell_size
        return (x, y)

    def neighbors(self, cell: GridCell, diagonal: bool = True) -> Iterable[GridCell]:
        """
        Vecinii liberi ai unei celule.

        Cu diagonal=True returnează 8-vecinătate (mișcări la 45°),
        altfel doar 4-vecinătate (sus/jos/stânga/dreapta).
        """
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
        for dr, dc in offsets:
            n = GridCell(cell.row + dr, cell.col + dc)
            if not self.is_free(n):
                continue
            if abs(dr) + abs(dc) == 2:
                if (
                    not self.is_free(GridCell(cell.row + dr, cell.col))
                    or not self.is_free(GridCell(cell.row, cell.col + dc))
                ):
                    continue
            yield n

    def inflate_obstacles(self, radius_cells: int) -> None:
        """
        Dilată obstacolele cu un raport de siguranță (în celule).

        Folosit pentru a marca celulele "prea aproape" de un obstacol ca
        ne-traversabile, ținând cont de raza fizică a robotului Pioneer.
        """
        if radius_cells <= 0:
            return
        try:
            from scipy.ndimage import binary_dilation  # type: ignore[import-not-found]

            structure = np.ones((2 * radius_cells + 1, 2 * radius_cells + 1), dtype=bool)
            self._occupancy = binary_dilation(self._occupancy, structure=structure)
        except ImportError:
            self._occupancy = self._dilate_numpy(self._occupancy, radius_cells)

    @staticmethod
    def _dilate_numpy(occ: np.ndarray, radius: int) -> np.ndarray:
        """Dilatare binară (Chebyshev) fără scipy — shift-uri pe matrice numpy."""
        out = occ.copy()
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if dr == 0 and dc == 0:
                    continue
                shifted = np.zeros_like(occ)
                r_src = slice(max(0, -dr), occ.shape[0] - max(0, dr))
                r_dst = slice(max(0, dr), occ.shape[0] - max(0, -dr))
                c_src = slice(max(0, -dc), occ.shape[1] - max(0, dc))
                c_dst = slice(max(0, dc), occ.shape[1] - max(0, -dc))
                shifted[r_dst, c_dst] = occ[r_src, c_src]
                out |= shifted
        return out

    @classmethod
    def from_array(
        cls,
        occupancy: np.ndarray,
        cell_size: float = 0.25,
        origin: tuple[float, float] = (0.0, 0.0),
    ) -> "GridMap":
        """Construiește un GridMap dintr-o matrice de ocupare existentă."""
        rows, cols = occupancy.shape
        grid = cls(rows=rows, cols=cols, cell_size=cell_size, origin=origin)
        grid._occupancy = occupancy.astype(bool)
        return grid

    def __repr__(self) -> str:
        free = int(np.sum(~self._occupancy))
        total = self.rows * self.cols
        return (
            f"GridMap({self.rows}×{self.cols}, cell={self.cell_size}m, "
            f"free={free}/{total})"
        )
