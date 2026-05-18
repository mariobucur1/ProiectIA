"""
Worker QThread care rulează algoritmul TSP în afara thread-ului UI.

Esențial pentru ca GUI-ul să rămână responsive în timpul rulărilor lungi
(Backtracking, ACO etc.). Emite semnale Qt pentru progres și rezultat final.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from ..algorithms import TSPAlgorithm
from ..core import AlgorithmResult, TSPProblem, Tour


class SolverWorker(QThread):
    """
    Thread care rulează un algoritm TSP și raportează progres către UI.

    Semnale:
        progress(int, float, Tour): iterație curentă, lungime, tur curent
        finished_with_result(AlgorithmResult): rezultatul final
        error(str): mesaj de eroare dacă rularea eșuează
    """

    progress = pyqtSignal(int, float, object)
    finished_with_result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, algorithm: TSPAlgorithm, problem: TSPProblem, parent=None):
        super().__init__(parent)
        self._algorithm = algorithm
        self._problem = problem
        self._stop_requested = False

    def request_stop(self) -> None:
        """Cere oprirea algoritmului (efectivă la următoarea verificare de timeout)."""
        self._stop_requested = True
        self._algorithm.config.time_limit_seconds = 0.001

    def run(self) -> None:
        try:
            result = self._algorithm.solve(
                self._problem,
                progress_callback=self._on_progress,
            )
            self.finished_with_result.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

    def _on_progress(self, iteration: int, length: float, tour: Tour) -> None:
        if not self._stop_requested:
            self.progress.emit(iteration, length, tour)
