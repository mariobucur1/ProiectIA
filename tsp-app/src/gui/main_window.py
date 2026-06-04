"""
Fereastra principală PyQt6 a aplicației TSP.

Layout:
    ┌────────────────────────────────────────────┐
    │ Toolbar: Load Local | Load URL | Run | Stop│
    ├──────────────┬─────────────────────────────┤
    │              │                             │
    │   Sidebar    │      TourCanvas             │
    │  (algoritmi  │   (vizualizare 2D)          │
    │   + parametri│                             │
    │   + export)  │                             │
    │              │                             │
    ├──────────────┴─────────────────────────────┤
    │  Status bar: iter, lungime, timp           │
    └────────────────────────────────────────────┘
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..algorithms import ALGORITHMS, AlgorithmConfig
from ..core import AlgorithmResult, TSPProblem
from ..io import (
    export_history_plot,
    export_result_to_csv,
    load_cities_from_csv,
    load_cities_from_json,
    load_cities_from_url,
)
from . import theme
from .assistant_panel import AssistantPanel
from .canvas import TourCanvas
from .parameter_panel import ParameterPanel
from .visualization_window import VisualizationWindow
from .worker import SolverWorker


REMOTE_PRESETS: list[tuple[str, str, str]] = [
    (
        "acu192 — tiny (10 orașe)",
        "https://raw.githubusercontent.com/acu192/fun-tsp-challenge/master/data/tiny.csv",
        "acu192-tiny-10",
    ),
    (
        "acu192 — small (30 orașe, clusterizate)",
        "https://raw.githubusercontent.com/acu192/fun-tsp-challenge/master/data/small.csv",
        "acu192-small-30",
    ),
    (
        "acu192 — medium (100 orașe)",
        "https://raw.githubusercontent.com/acu192/fun-tsp-challenge/master/data/medium.csv",
        "acu192-medium-100",
    ),
    (
        "acu192 — large (1000 orașe)",
        "https://raw.githubusercontent.com/acu192/fun-tsp-challenge/master/data/large.csv",
        "acu192-large-1000",
    ),
]


class MainWindow(QMainWindow):
    """Fereastra principală a aplicației TSP."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proiect IA — Comis-Voiajor (TSP) — USV")
        self.resize(1280, 800)

        self._problem: Optional[TSPProblem] = None
        self._worker: Optional[SolverWorker] = None
        self._last_results: list[AlgorithmResult] = []
        self._run_start_time: float = 0.0
        self._viz_window: Optional[VisualizationWindow] = None

        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        self._build_toolbar()
        self._build_central()
        self._build_assistant_dock()
        self._build_status_bar()

    def _build_assistant_dock(self) -> None:
        self._assistant = AssistantPanel()
        self._assistant_dock = QDockWidget("Asistent AI", self)
        self._assistant_dock.setObjectName("assistant_dock")
        self._assistant_dock.setWidget(self._assistant)
        self._assistant_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._assistant_dock.setMinimumWidth(340)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._assistant_dock)
        self._assistant_dock.hide()
        # sincronizează butonul din toolbar cu vizibilitatea dock-ului
        self._assistant_dock.visibilityChanged.connect(self._assistant_action.setChecked)
        self._assistant.set_current_algorithm(self._algorithm_combo.currentText())

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Acțiuni principale")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        load_csv = QAction("Încarcă CSV…", self)
        load_csv.triggered.connect(self._on_load_csv)
        toolbar.addAction(load_csv)

        load_json = QAction("Încarcă JSON…", self)
        load_json.triggered.connect(self._on_load_json)
        toolbar.addAction(load_json)

        load_url = QAction("Încarcă de pe GitHub…", self)
        load_url.triggered.connect(self._on_load_url)
        toolbar.addAction(load_url)

        presets_btn = QToolButton(self)
        presets_btn.setText("Dataseturi publice ▾")
        presets_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        presets_menu = QMenu(presets_btn)
        for label, url, name in REMOTE_PRESETS:
            act = QAction(label, self)
            act.triggered.connect(lambda _checked=False, u=url, n=name: self._on_load_preset(u, n))
            presets_menu.addAction(act)
        presets_btn.setMenu(presets_menu)
        toolbar.addWidget(presets_btn)

        toolbar.addSeparator()

        self._run_action = QAction("▶ Rulează", self)
        self._run_action.triggered.connect(self._on_run)
        toolbar.addAction(self._run_action)

        self._stop_action = QAction("■ Oprește", self)
        self._stop_action.setEnabled(False)
        self._stop_action.triggered.connect(self._on_stop)
        toolbar.addAction(self._stop_action)

        toolbar.addSeparator()

        viz_action = QAction("🔍 Vizualizare live", self)
        viz_action.triggered.connect(self._on_open_visualization)
        toolbar.addAction(viz_action)

        self._assistant_action = QAction("🤖 Asistent AI", self)
        self._assistant_action.setCheckable(True)
        self._assistant_action.triggered.connect(self._on_toggle_assistant)
        toolbar.addAction(self._assistant_action)

        toolbar.addSeparator()

        export_csv = QAction("Export CSV rezultate", self)
        export_csv.triggered.connect(self._on_export_csv)
        toolbar.addAction(export_csv)

        export_plot = QAction("Export grafic convergență", self)
        export_plot.triggered.connect(self._on_export_plot)
        toolbar.addAction(export_plot)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)

        sidebar_layout.addWidget(QLabel("Algoritm:"))
        self._algorithm_combo = QComboBox()
        self._algorithm_combo.addItems(list(ALGORITHMS.keys()))
        self._algorithm_combo.currentTextChanged.connect(self._on_algorithm_changed)
        sidebar_layout.addWidget(self._algorithm_combo)

        self._parameter_panel = ParameterPanel()
        scroll = QScrollArea()
        scroll.setWidget(self._parameter_panel)
        scroll.setWidgetResizable(True)
        sidebar_layout.addWidget(scroll, 1)

        self._results_label = QLabel("Niciun rezultat încă.")
        self._results_label.setWordWrap(True)
        self._results_label.setStyleSheet(
            f"padding: 8px; background: {theme.SURFACE}; "
            f"border: 1px solid {theme.BORDER}; border-radius: 6px;"
        )
        sidebar_layout.addWidget(self._results_label)

        sidebar.setMinimumWidth(320)
        sidebar.setMaximumWidth(420)
        splitter.addWidget(sidebar)

        self._canvas = TourCanvas()
        splitter.addWidget(self._canvas)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([350, 900])

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self._parameter_panel.set_algorithm(self._algorithm_combo.currentText())

    def _build_status_bar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self._status_label = QLabel("Pregătit.")
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setMaximumWidth(180)
        status.addWidget(self._status_label, 1)
        status.addPermanentWidget(self._progress_bar)

    def _apply_theme(self) -> None:
        self.setStyleSheet(theme.app_stylesheet())

    def _on_algorithm_changed(self, name: str) -> None:
        self._parameter_panel.set_algorithm(name)
        if hasattr(self, "_assistant"):
            self._assistant.set_current_algorithm(name)

    def _on_toggle_assistant(self, checked: bool) -> None:
        self._assistant_dock.setVisible(checked)
        if checked:
            self._assistant.set_context(
                self._last_results, self._problem, self._algorithm_combo.currentText()
            )
            self._assistant_dock.raise_()

    def _on_load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selectează fișier CSV", str(Path.cwd()), "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            problem = load_cities_from_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "Eroare la încărcare", str(exc))
            return
        self._set_problem(problem)

    def _on_load_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selectează fișier JSON", str(Path.cwd()), "JSON files (*.json)"
        )
        if not path:
            return
        try:
            problem = load_cities_from_json(path)
        except Exception as exc:
            QMessageBox.critical(self, "Eroare la încărcare", str(exc))
            return
        self._set_problem(problem)

    def _on_load_preset(self, url: str, name: str) -> None:
        self._status_label.setText(f"Descarc {name}…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            problem = load_cities_from_url(url, problem_name=name)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Eroare la descărcare", f"{name}\n\n{exc}")
            self._status_label.setText("Pregătit.")
            return
        QApplication.restoreOverrideCursor()
        self._set_problem(problem)

    def _on_load_url(self) -> None:
        url, ok = QInputDialog.getText(
            self,
            "Încarcă de pe GitHub",
            "URL raw GitHub (.csv sau .json):",
            text="https://raw.githubusercontent.com/",
        )
        if not ok or not url.strip():
            return
        try:
            problem = load_cities_from_url(url.strip())
        except Exception as exc:
            QMessageBox.critical(self, "Eroare la descărcare", str(exc))
            return
        self._set_problem(problem)

    def _set_problem(self, problem: TSPProblem) -> None:
        self._problem = problem
        self._canvas.set_problem(problem)
        if self._viz_window is not None:
            self._viz_window.set_problem(problem)
        self._status_label.setText(
            f"Încărcat: {problem.name} ({problem.n} orașe)."
        )
        if hasattr(self, "_assistant"):
            self._assistant.set_context(
                self._last_results, problem, self._algorithm_combo.currentText()
            )

    def _ensure_viz_window(self) -> VisualizationWindow:
        if self._viz_window is None:
            self._viz_window = VisualizationWindow(self)
            if self._problem is not None:
                self._viz_window.set_problem(self._problem)
        return self._viz_window

    def _on_open_visualization(self) -> None:
        win = self._ensure_viz_window()
        if not win.isVisible():
            win.show()
        win.raise_()
        win.activateWindow()

    def _on_run(self) -> None:
        if self._problem is None:
            QMessageBox.information(self, "Atenție", "Încarcă întâi un set de date.")
            return
        if self._worker is not None and self._worker.isRunning():
            return

        name = self._algorithm_combo.currentText()
        params = self._parameter_panel.get_values()

        config = AlgorithmConfig()
        if "max_iterations" in params:
            config.max_iterations = int(params.pop("max_iterations"))
        if "time_limit_seconds" in params:
            config.time_limit_seconds = float(params.pop("time_limit_seconds"))
        config.extra = params

        algorithm = ALGORITHMS[name](config)
        self._worker = SolverWorker(algorithm, self._problem, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_with_result.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        viz = self._ensure_viz_window()
        viz.start_run(name)

        self._run_action.setEnabled(False)
        self._stop_action.setEnabled(True)
        self._progress_bar.setVisible(True)
        self._run_start_time = time.perf_counter()
        self._status_label.setText(f"Rulez {name}…")
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.request_stop()
            self._status_label.setText("Oprire cerută…")

    def _on_progress(self, iteration: int, length: float, tour) -> None:
        elapsed = time.perf_counter() - self._run_start_time
        self._canvas.set_tour(
            tour,
            info=f"{self._algorithm_combo.currentText()} — iter {iteration}, lungime {length:.2f}",
        )
        if self._viz_window is not None:
            self._viz_window.on_progress(iteration, length, tour)
        self._status_label.setText(
            f"iter {iteration} | lungime {length:.2f} | timp {elapsed:.1f}s"
        )

    def _on_finished(self, result: AlgorithmResult) -> None:
        self._last_results.append(result)
        self._canvas.set_tour(result.best_tour, info=f"{result.algorithm_name} — FINAL")
        self._canvas.set_best_tour(result.best_tour)
        if self._viz_window is not None:
            self._viz_window.on_finished(result)
        self._results_label.setText(
            f"<b>{result.algorithm_name}</b><br>"
            f"Lungime: <b>{result.best_length:.2f}</b><br>"
            f"Timp: {result.elapsed_seconds:.3f} s<br>"
            f"Iterații: {result.iterations}"
        )
        self._status_label.setText(
            f"Gata: {result.algorithm_name} — lungime {result.best_length:.2f} ({result.elapsed_seconds:.2f}s)"
        )
        if hasattr(self, "_assistant"):
            self._assistant.set_context(
                self._last_results, self._problem, self._algorithm_combo.currentText()
            )
        self._cleanup_worker()

    def _on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Eroare la rulare", message)
        self._status_label.setText(f"Eroare: {message}")
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        self._run_action.setEnabled(True)
        self._stop_action.setEnabled(False)
        self._progress_bar.setVisible(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _on_export_csv(self) -> None:
        if not self._last_results:
            QMessageBox.information(self, "Atenție", "Nu există rezultate de exportat.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvează CSV", "rezultate.csv", "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            export_result_to_csv(self._last_results, path)
        except Exception as exc:
            QMessageBox.critical(self, "Eroare la export", str(exc))
            return
        self._status_label.setText(f"Export CSV: {path}")

    def _on_export_plot(self) -> None:
        if not self._last_results:
            QMessageBox.information(self, "Atenție", "Nu există rezultate de exportat.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvează grafic", "convergenta.png", "PNG files (*.png)"
        )
        if not path:
            return
        try:
            export_history_plot(self._last_results, path)
        except Exception as exc:
            QMessageBox.critical(self, "Eroare la export", str(exc))
            return
        self._status_label.setText(f"Export grafic: {path}")
