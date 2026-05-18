"""Teste unitare pentru modulul core (City, Tour, TSPProblem)."""

import math

import numpy as np
import pytest

from src.core import City, Tour, TSPProblem


def make_problem():
    cities = [
        City(0, "A", 0.0, 0.0),
        City(1, "B", 3.0, 0.0),
        City(2, "C", 3.0, 4.0),
        City(3, "D", 0.0, 4.0),
    ]
    return TSPProblem(cities, name="Square4")


def test_city_distance():
    a = City(0, "A", 0.0, 0.0)
    b = City(1, "B", 3.0, 4.0)
    assert a.distance_to(b) == pytest.approx(5.0)


def test_problem_distance_matrix_symmetric():
    problem = make_problem()
    d = problem.distance_matrix
    assert d.shape == (4, 4)
    np.testing.assert_allclose(d, d.T)
    np.testing.assert_allclose(np.diag(d), 0.0)


def test_problem_distance_matrix_readonly():
    problem = make_problem()
    with pytest.raises(ValueError):
        problem.distance_matrix[0, 1] = 999.0


def test_tour_length_square():
    problem = make_problem()
    tour = Tour([0, 1, 2, 3])
    assert problem.tour_length(tour) == pytest.approx(14.0)


def test_tour_length_cached():
    problem = make_problem()
    tour = Tour([0, 1, 2, 3])
    first = problem.tour_length(tour)
    second = problem.tour_length(tour)
    assert first == second


def test_tour_swap_invalidates_cache():
    problem = make_problem()
    tour = Tour([0, 1, 2, 3])
    problem.tour_length(tour)
    tour.swap(1, 2)
    new_length = problem.tour_length(tour)
    assert new_length == pytest.approx(2 * math.hypot(3.0, 4.0) + 3.0 + 3.0, rel=1e-6)


def test_tour_reverse_segment():
    tour = Tour([0, 1, 2, 3, 4])
    tour.reverse_segment(1, 3)
    assert list(tour) == [0, 3, 2, 1, 4]
