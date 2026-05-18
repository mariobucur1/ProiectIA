"""Teste A* + GridMap (fără CoppeliaSim — doar partea algoritmică)."""

import pytest

from src.algorithms import AStarPathfinder, NoPathFoundError
from src.world import GridCell, GridMap


def test_grid_world_conversion():
    gm = GridMap(rows=10, cols=10, cell_size=0.5, origin=(-2.0, -2.0))
    cell = gm.world_to_grid(0.0, 0.0)
    assert cell == GridCell(4, 4)
    x, y = gm.grid_to_world(GridCell(4, 4))
    assert x == pytest.approx(0.25)
    assert y == pytest.approx(0.25)


def test_astar_empty_grid_diagonal():
    gm = GridMap(rows=10, cols=10)
    pf = AStarPathfinder(gm)
    path = pf.find_path(GridCell(0, 0), GridCell(9, 9))
    assert path[0] == GridCell(0, 0)
    assert path[-1] == GridCell(9, 9)
    assert len(path) == 10


def test_astar_with_obstacle():
    gm = GridMap(rows=5, cols=5)
    gm.add_rectangle_obstacle(GridCell(2, 0), GridCell(2, 3))
    pf = AStarPathfinder(gm)
    path = pf.find_path(GridCell(0, 0), GridCell(4, 0))
    assert path[0] == GridCell(0, 0)
    assert path[-1] == GridCell(4, 0)
    for cell in path:
        assert gm.is_free(cell)


def test_astar_no_path():
    gm = GridMap(rows=5, cols=5)
    gm.add_rectangle_obstacle(GridCell(2, 0), GridCell(2, 4))
    pf = AStarPathfinder(gm)
    with pytest.raises(NoPathFoundError):
        pf.find_path(GridCell(0, 0), GridCell(4, 0))


def test_astar_start_equals_goal():
    gm = GridMap(rows=5, cols=5)
    pf = AStarPathfinder(gm)
    path = pf.find_path(GridCell(2, 2), GridCell(2, 2))
    assert path == [GridCell(2, 2)]


def test_smooth_path_reduces_waypoints():
    gm = GridMap(rows=10, cols=10)
    pf = AStarPathfinder(gm)
    path = pf.find_path(GridCell(0, 0), GridCell(9, 9))
    smoothed = AStarPathfinder.smooth_path(path, gm)
    assert smoothed[0] == path[0]
    assert smoothed[-1] == path[-1]
    assert len(smoothed) <= len(path)
