"""
Fereastră separată de vizualizare live pentru rularea algoritmilor TSP.

Conține:
- TourGraphicsView: tur desenat cu QGraphicsView (zoom rotiță, pan drag).
- Plot de convergență matplotlib actualizat în timp real cu toolbar Qt
  (zoom rectangle, pan, save PNG, reset).
- Bară de stare cu iterația curentă, lungime, cel mai bun rezultat și timp.
"""

from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from ..core import AlgorithmResult, TSPProblem, Tour


_BG = "#1e1e2e"
_BG_DARK = "#181825"
_FG = "#cdd6f4"
_GRID = "#45475a"
_CITY = QColor("#89b4fa")
_CITY_BORDER = QColor("#cdd6f4")
_TOUR = QColor("#a6e3a1")
_BEST = QColor("#f9e2af")
_START = QColor("#f38ba8")


class TourGraphicsView(QGraphicsView):
    """QGraphicsView cu zoom (wheel) și pan (drag) pentru turul TSP."""

    CITY_RADIUS = 6.0
    SCENE_SIZE = 1000.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(_BG)))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        self._problem: Optional[TSPProblem] = None
        self._tour_item = None
        self._best_tour_item = None
        self._city_items: list = []
        self._label_items: list = []
        self._show_labels = True

        self._min_x = 0.0
        self._min_y = 0.0
        self._scale = 1.0

    def set_problem(self, problem: Optional[TSPProblem]) -> None:
        self._scene.clear()
        self._tour_item = None
        self._best_tour_item = None
        self._city_items = []
        self._label_items = []
        self._problem = problem

        if problem is None:
            return

        cities = problem.cities
        xs = [c.x for c in cities]
        ys = [c.y for c in cities]
        self._min_x = min(xs)
        self._min_y = min(ys)
        range_x = max(max(xs) - self._min_x, 1e-6)
        range_y = max(max(ys) - self._min_y, 1e-6)
        self._scale = self.SCENE_SIZE / max(range_x, range_y)

        for i, city in enumerate(cities):
            p = self._to_scene(city.x, city.y)
            r = self.CITY_RADIUS
            brush_color = _START if i == 0 else _CITY
            ellipse = self._scene.addEllipse(
                p.x() - r, p.y() - r, 2 * r, 2 * r,
                QPen(_CITY_BORDER, 1),
                QBrush(brush_color),
            )
            ellipse.setZValue(2)
            self._city_items.append(ellipse)

            label = self._scene.addSimpleText(city.name, QFont("Segoe UI", 8))
            label.setBrush(QBrush(QColor(_FG)))
            label.setPos(p.x() + r + 2, p.y() - r)
            label.setVisible(self._show_labels)
            label.setZValue(3)
            self._label_items.append(label)

        self.reset_view()

    def _to_scene(self, x: float, y: float) -> QPointF:
        return QPointF(
            (x - self._min_x) * self._scale,
            -(y - self._min_y) * self._scale,
        )

    def _build_path(self, tour: Tour) -> QPainterPath:
        path = QPainterPath()
        order = list(tour)
        if not order or self._problem is None:
            return path
        cities = self._problem.cities
        first = self._to_scene(cities[order[0]].x, cities[order[0]].y)
        path.moveTo(first)
        for idx in order[1:]:
            p = self._to_scene(cities[idx].x, cities[idx].y)
            path.lineTo(p)
        path.lineTo(first)
        return path

    def set_tour(self, tour: Optional[Tour]) -> None:
        if self._problem is None or tour is None:
            return
        path = self._build_path(tour)
        if self._tour_item is None:
            pen = QPen(_TOUR, 2.0)
            pen.setCosmetic(True)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            self._tour_item = self._scene.addPath(path, pen)
            self._tour_item.setZValue(1)
        else:
            self._tour_item.setPath(path)

    def set_best_tour(self, tour: Optional[Tour]) -> None:
        if self._problem is None or tour is None:
            return
        path = self._build_path(tour)
        if self._best_tour_item is None:
            color = QColor(_BEST)
            color.setAlpha(110)
            pen = QPen(color, 1.5)
            pen.setCosmetic(True)
            self._best_tour_item = self._scene.addPath(path, pen)
            self._best_tour_item.setZValue(0)
        else:
            self._best_tour_item.setPath(path)

    def set_show_labels(self, show: bool) -> None:
        self._show_labels = show
        for label in self._label_items:
            label.setVisible(show)

    def reset_view(self) -> None:
        rect = self._scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        margin = max(rect.width(), rect.height()) * 0.05
        rect = rect.adjusted(-margin, -margin, margin, margin)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        angle = event.angleDelta().y()
        if angle == 0:
            return
        factor = 1.15 if angle > 0 else 1 / 1.15
        self.scale(factor, factor)


class VisualizationWindow(QDialog):
    """Fereastră non-modală cu turul live + plot de convergență."""

    PLOT_REDRAW_INTERVAL = 0.15  # secunde — throttle pentru redesen matplotlib

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vizualizare live — TSP")
        self.resize(1200, 720)
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.Window, True)

        self._algorithm_name = ""
        self._convergence: list[float] = []
        self._best_length: float = float("inf")
        self._run_start: float = 0.0
        self._last_plot_redraw: float = 0.0

        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        bar = QHBoxLayout()
        self._reset_btn = QPushButton("Resetează zoom")
        self._reset_btn.clicked.connect(self._on_reset_view)
        self._labels_chk = QCheckBox("Afișează etichete orașe")
        self._labels_chk.setChecked(True)
        self._labels_chk.toggled.connect(self._on_toggle_labels)
        bar.addWidget(self._reset_btn)
        bar.addWidget(self._labels_chk)
        bar.addStretch(1)
        self._stats_label = QLabel("Așteaptă o rulare…")
        self._stats_label.setStyleSheet("font-weight: bold; padding: 4px 8px;")
        bar.addWidget(self._stats_label)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._tour_view = TourGraphicsView()
        splitter.addWidget(self._tour_view)

        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(figsize=(5, 4), facecolor=_BG)
        self._ax = self._figure.add_subplot(111)
        self._configure_axes()
        (self._line,) = self._ax.plot([], [], color="#a6e3a1", linewidth=1.5, label="Lungime curentă")
        (self._best_line,) = self._ax.plot([], [], color="#f9e2af", linewidth=1.2, linestyle="--", label="Cea mai bună")
        self._ax.legend(loc="upper right", facecolor=_BG_DARK, edgecolor=_GRID, labelcolor=_FG)

        self._canvas = FigureCanvas(self._figure)
        self._nav_toolbar = NavigationToolbar(self._canvas, self)
        plot_layout.addWidget(self._nav_toolbar)
        plot_layout.addWidget(self._canvas)
        splitter.addWidget(plot_widget)

        splitter.setSizes([720, 480])
        root.addWidget(splitter, 1)

    def _configure_axes(self) -> None:
        self._ax.set_facecolor(_BG_DARK)
        self._ax.tick_params(colors=_FG)
        for spine in self._ax.spines.values():
            spine.set_color(_GRID)
        self._ax.set_xlabel("Iterație", color=_FG)
        self._ax.set_ylabel("Lungime tur", color=_FG)
        self._ax.set_title("Convergență", color=_FG)
        self._ax.grid(True, alpha=0.3, color=_GRID)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: {_BG}; color: {_FG}; }}
            QLabel, QCheckBox {{ color: {_FG}; }}
            QPushButton {{
                background-color: #313244; color: {_FG};
                border: 1px solid {_GRID}; padding: 6px 10px; border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {_GRID}; }}
            QToolBar {{ background-color: {_BG_DARK}; border: none; }}
            """
        )

    def set_problem(self, problem: Optional[TSPProblem]) -> None:
        self._tour_view.set_problem(problem)
        self._convergence.clear()
        self._best_length = float("inf")
        self._line.set_data([], [])
        self._best_line.set_data([], [])
        self._ax.relim()
        self._ax.autoscale_view()
        self._canvas.draw_idle()
        if problem is not None:
            self._stats_label.setText(f"{problem.name} — {problem.n} orașe")

    def start_run(self, algorithm_name: str) -> None:
        self._algorithm_name = algorithm_name
        self._convergence.clear()
        self._best_length = float("inf")
        self._run_start = time.perf_counter()
        self._last_plot_redraw = 0.0
        self._line.set_data([], [])
        self._best_line.set_data([], [])
        self._ax.set_title(f"Convergență — {algorithm_name}", color=_FG)
        self._canvas.draw_idle()
        self._stats_label.setText(f"{algorithm_name} — start…")
        if not self.isVisible():
            self.show()
        self.raise_()

    def on_progress(self, iteration: int, length: float, tour: Tour) -> None:
        self._tour_view.set_tour(tour)
        self._convergence.append(length)
        if length < self._best_length:
            self._best_length = length

        now = time.perf_counter()
        if now - self._last_plot_redraw > self.PLOT_REDRAW_INTERVAL:
            self._redraw_plot()
            self._last_plot_redraw = now

        elapsed = now - self._run_start
        self._stats_label.setText(
            f"{self._algorithm_name} — iter {iteration} | "
            f"curent {length:.2f} | best {self._best_length:.2f} | {elapsed:.1f}s"
        )

    def on_finished(self, result: AlgorithmResult) -> None:
        if result.convergence_history:
            self._convergence = list(result.convergence_history)
            self._best_length = min(self._convergence)
        self._tour_view.set_tour(result.best_tour)
        self._tour_view.set_best_tour(result.best_tour)
        self._redraw_plot()
        self._stats_label.setText(
            f"{result.algorithm_name} — FINAL | lungime {result.best_length:.2f} | "
            f"{result.elapsed_seconds:.2f}s | {result.iterations} iter"
        )

    def _redraw_plot(self) -> None:
        if not self._convergence:
            return
        xs = list(range(len(self._convergence)))
        self._line.set_data(xs, self._convergence)

        running_best: list[float] = []
        cur = float("inf")
        for v in self._convergence:
            if v < cur:
                cur = v
            running_best.append(cur)
        self._best_line.set_data(xs, running_best)

        self._ax.relim()
        self._ax.autoscale_view()
        self._canvas.draw_idle()

    def _on_reset_view(self) -> None:
        self._tour_view.reset_view()

    def _on_toggle_labels(self, checked: bool) -> None:
        self._tour_view.set_show_labels(checked)
