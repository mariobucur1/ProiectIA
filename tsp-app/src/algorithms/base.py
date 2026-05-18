"""Interfață comună pentru toți algoritmii TSP."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..core import AlgorithmResult, TSPProblem, Tour


ProgressCallback = Callable[[int, float, Tour], None]
"""Semnătura unui callback de progres: (iterație, lungime_curentă, tur_curent)."""


@dataclass
class AlgorithmConfig:
    """
    Configurația comună pentru toți algoritmii.

    Subclasele algoritmilor pot extinde dataclass-ul cu parametri proprii
    (ex. temperatura inițială pentru SA, populație pentru GA etc.).
    """

    max_iterations: int = 1000
    time_limit_seconds: Optional[float] = None
    seed: Optional[int] = None
    verbose: bool = False
    extra: dict = field(default_factory=dict)


class TSPAlgorithm(ABC):
    """
    Clasa de bază pentru orice algoritm TSP.

    Subclasele implementează `_solve()` care primește problema și callback-ul
    de progres și returnează AlgorithmResult. Wrapper-ul `solve()` măsoară
    automat timpul și asigură un comportament uniform.
    """

    name: str = "AbstractAlgorithm"

    def __init__(self, config: AlgorithmConfig | None = None):
        self.config = config or AlgorithmConfig()

    def solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> AlgorithmResult:
        """Rulează algoritmul și măsoară timpul de execuție."""
        start = time.perf_counter()
        result = self._solve(problem, progress_callback)
        result.elapsed_seconds = time.perf_counter() - start
        return result

    @abstractmethod
    def _solve(
        self,
        problem: TSPProblem,
        progress_callback: Optional[ProgressCallback],
    ) -> AlgorithmResult:
        """Implementarea efectivă a algoritmului. Suprascris de fiecare subclasă."""

    def _should_stop(self, iteration: int, start_time: float) -> bool:
        """Verifică condițiile de oprire (iterații + timeout)."""
        if iteration >= self.config.max_iterations:
            return True
        if self.config.time_limit_seconds is not None:
            if (time.perf_counter() - start_time) >= self.config.time_limit_seconds:
                return True
        return False
