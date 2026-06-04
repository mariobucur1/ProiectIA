"""
Widget de vizualizare pentru orașe și tur.

Desenează:
- Orașele ca puncte (cu eticheta numelui)
- Turul curent ca linii poligonale
- Distanța totală în colțul stânga-sus
- Auto-scaling pentru a încadra toate orașele în zona vizibilă
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..core import TSPProblem, Tour
from . import theme


class TourCanvas(QWidget):
    """Suprafață custom-paint pentru vizualizarea TSP."""

    BACKGROUND = QColor(theme.VIZ_BG)
    CITY_COLOR = QColor(theme.VIZ_CITY)
    CITY_BORDER = QColor(theme.VIZ_CITY_BORDER)
    TOUR_COLOR = QColor(theme.VIZ_TOUR)
    BEST_TOUR_COLOR = QColor(theme.VIZ_BEST)
    TEXT_COLOR = QColor(theme.TEXT)
    START_CITY_COLOR = QColor(theme.VIZ_START)

    PADDING = 30
    CITY_RADIUS = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._problem: Optional[TSPProblem] = None
        self._tour: Optional[Tour] = None
        self._best_tour: Optional[Tour] = None
        self._info_text = ""
        self._show_labels = True
        self.setMinimumSize(500, 400)
        self.setAutoFillBackground(False)

    def set_problem(self, problem: Optional[TSPProblem]) -> None:
        self._problem = problem
        self._tour = None
        self._best_tour = None
        self._info_text = (
            f"{problem.name} — {problem.n} orașe" if problem else ""
        )
        self.update()

    def set_tour(self, tour: Optional[Tour], info: str = "") -> None:
        self._tour = tour
        if info:
            self._info_text = info
        self.update()

    def set_best_tour(self, tour: Optional[Tour]) -> None:
        self._best_tour = tour
        self.update()

    def set_show_labels(self, show: bool) -> None:
        self._show_labels = show
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.BACKGROUND)

        if self._problem is None:
            painter.setPen(self.TEXT_COLOR)
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(
                self.rect(),
                int(Qt.AlignmentFlag.AlignCenter),
                "Încarcă un set de date pentru a începe.",
            )
            return

        transform = self._compute_transform()
        if self._best_tour is not None:
            self._draw_tour(painter, self._best_tour, transform, self.BEST_TOUR_COLOR, width=1.5, alpha=80)
        if self._tour is not None:
            self._draw_tour(painter, self._tour, transform, self.TOUR_COLOR, width=2.0)

        self._draw_cities(painter, transform)
        self._draw_info(painter)

    def _compute_transform(self):
        cities = self._problem.cities
        xs = [c.x for c in cities]
        ys = [c.y for c in cities]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max(max_x - min_x, 1e-6)
        range_y = max(max_y - min_y, 1e-6)

        w = self.width() - 2 * self.PADDING
        h = self.height() - 2 * self.PADDING
        scale = min(w / range_x, h / range_y)

        offset_x = self.PADDING + (w - range_x * scale) / 2
        offset_y = self.PADDING + (h - range_y * scale) / 2

        def to_screen(x: float, y: float) -> QPointF:
            sx = offset_x + (x - min_x) * scale
            sy = self.height() - (offset_y + (y - min_y) * scale)
            return QPointF(sx, sy)

        return to_screen

    def _draw_tour(self, painter, tour, transform, color, width=2.0, alpha=255):
        pen_color = QColor(color)
        pen_color.setAlpha(alpha)
        pen = QPen(pen_color, width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        order = list(tour)
        cities = self._problem.cities
        points = [transform(cities[i].x, cities[i].y) for i in order]
        points.append(points[0])
        for p1, p2 in zip(points[:-1], points[1:]):
            painter.drawLine(p1, p2)

    def _draw_cities(self, painter, transform):
        painter.setFont(QFont("Segoe UI", 8))
        for i, city in enumerate(self._problem.cities):
            pt = transform(city.x, city.y)
            color = self.START_CITY_COLOR if i == 0 else self.CITY_COLOR
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(self.CITY_BORDER, 1))
            r = self.CITY_RADIUS
            painter.drawEllipse(QRectF(pt.x() - r, pt.y() - r, 2 * r, 2 * r))

            if self._show_labels:
                painter.setPen(self.TEXT_COLOR)
                painter.drawText(QPointF(pt.x() + r + 2, pt.y() - r), city.name)

    def _draw_info(self, painter):
        if not self._info_text:
            return
        painter.setPen(self.TEXT_COLOR)
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QPointF(10, 20), self._info_text)
