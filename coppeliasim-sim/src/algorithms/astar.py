"""
Algoritm A* pentru navigare pe grid 2D.

Funcția de evaluare:
    f(n) = g(n) + h(n)

unde:
    g(n) = costul real de la start până la n (suma muchiilor parcurse)
    h(n) = euristica — Distanța Euclidiană până la țintă (admisibilă)

A* găsește **calea optimă** dacă h(n) nu supraestimează costul real
(condiția de admisibilitate). Folosim Distanța Euclidiană deoarece:
- Robotul Pioneer P3-DX se poate roti liber, deci se poate deplasa
  pe diagonale (nu doar pe direcții perpendiculare ca în Manhattan).
- O linie dreaptă este întotdeauna mai scurtă sau egală cu orice
  drum printre obstacole → euristica este admisibilă.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from math import hypot
from typing import Optional

from ..world import GridCell, GridMap


class NoPathFoundError(RuntimeError):
    """Ridicată când nu există drum între start și goal."""


@dataclass(order=True)
class _PriorityNode:
    """Wrapper pentru heap: comparare după f, apoi după contor pentru stabilitate."""
    priority: float
    counter: int
    cell: GridCell = field(compare=False)


class AStarPathfinder:
    """
    Implementare A* pe `GridMap`, cu euristică Euclidiană și 8-vecinătate.

    Costul muchiei este:
        1.0          pentru mișcări ortogonale
        √2 ≈ 1.414   pentru mișcări diagonale
    multiplicat cu `cell_size` pentru a obține distanța reală în metri.
    """

    DIAG_COST = 2 ** 0.5

    def __init__(self, grid_map: GridMap):
        self.grid_map = grid_map

    def find_path(
        self, start: GridCell, goal: GridCell, allow_diagonal: bool = True
    ) -> list[GridCell]:
        """
        Returnează drumul ca listă de celule de la start până la goal (inclusiv).

        Aruncă `NoPathFoundError` dacă nu există drum.
        """
        gm = self.grid_map
        if not gm.is_free(start):
            raise NoPathFoundError(f"Celula de start {start} este blocată.")
        if not gm.is_free(goal):
            raise NoPathFoundError(f"Celula țintă {goal} este blocată.")
        if start == goal:
            return [start]

        open_heap: list[_PriorityNode] = []
        counter = 0
        g_score: dict[GridCell, float] = {start: 0.0}
        came_from: dict[GridCell, GridCell] = {}

        heapq.heappush(open_heap, _PriorityNode(self._heuristic(start, goal), counter, start))
        in_open: set[GridCell] = {start}
        closed: set[GridCell] = set()

        while open_heap:
            node = heapq.heappop(open_heap)
            current = node.cell

            if current in closed:
                continue
            if current == goal:
                return self._reconstruct(came_from, current)

            in_open.discard(current)
            closed.add(current)

            for neighbor in gm.neighbors(current, diagonal=allow_diagonal):
                if neighbor in closed:
                    continue
                step_cost = self._step_cost(current, neighbor)
                tentative_g = g_score[current] + step_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + self._heuristic(neighbor, goal)
                    counter += 1
                    heapq.heappush(open_heap, _PriorityNode(f, counter, neighbor))
                    in_open.add(neighbor)

        raise NoPathFoundError(f"Niciun drum de la {start} la {goal}.")

    def find_path_world(
        self,
        start_xy: tuple[float, float],
        goal_xy: tuple[float, float],
        allow_diagonal: bool = True,
    ) -> list[tuple[float, float]]:
        """Variantă cu coordonate world (metri). Returnează waypoints world."""
        start = self.grid_map.world_to_grid(*start_xy)
        goal = self.grid_map.world_to_grid(*goal_xy)
        cells = self.find_path(start, goal, allow_diagonal=allow_diagonal)
        return [self.grid_map.grid_to_world(c) for c in cells]

    def _heuristic(self, a: GridCell, b: GridCell) -> float:
        """Distanța Euclidiană (admisibilă, optimă cu 8-vecinătate)."""
        return hypot(a.row - b.row, a.col - b.col)

    def _step_cost(self, a: GridCell, b: GridCell) -> float:
        if a.row != b.row and a.col != b.col:
            return self.DIAG_COST
        return 1.0

    @staticmethod
    def _reconstruct(came_from: dict[GridCell, GridCell], end: GridCell) -> list[GridCell]:
        path = [end]
        while end in came_from:
            end = came_from[end]
            path.append(end)
        path.reverse()
        return path

    @staticmethod
    def smooth_path(path: list[GridCell], grid_map: GridMap) -> list[GridCell]:
        """
        Smoothing cu line-of-sight (algoritm "string-pulling").

        Elimină waypoints inutile dacă există linie dreaptă liberă între
        două puncte ne-adiacente. Reduce mișcările de zig-zag pe diagonale.
        """
        if len(path) <= 2:
            return path
        smoothed = [path[0]]
        anchor = 0
        for i in range(2, len(path)):
            if not AStarPathfinder._has_line_of_sight(path[anchor], path[i], grid_map):
                smoothed.append(path[i - 1])
                anchor = i - 1
        smoothed.append(path[-1])
        return smoothed

    @staticmethod
    def _has_line_of_sight(a: GridCell, b: GridCell, grid_map: GridMap) -> bool:
        """Algoritm Bresenham pentru linie discretă; verifică toate celulele."""
        r0, c0 = a.row, a.col
        r1, c1 = b.row, b.col
        dr = abs(r1 - r0)
        dc = abs(c1 - c0)
        sr = 1 if r0 < r1 else -1
        sc = 1 if c0 < c1 else -1
        err = dr - dc

        while True:
            if not grid_map.is_free(GridCell(r0, c0)):
                return False
            if r0 == r1 and c0 == c1:
                return True
            e2 = 2 * err
            if e2 > -dc:
                err -= dc
                r0 += sr
            if e2 < dr:
                err += dr
                c0 += sc
