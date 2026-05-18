"""
Panou dinamic de parametri — se schimbă în funcție de algoritmul selectat.

Fiecare algoritm are propriul set de parametri (definit în SCHEMA), iar UI-ul
este generat automat din schema. Astfel adăugarea unui algoritm nou
necesită doar o intrare în SCHEMA.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ParamSpec:
    """Specificația unui parametru: tip, valori implicite, limite."""

    label: str
    kind: str
    default: Any
    minimum: float = 0.0
    maximum: float = 1e9
    step: float = 1.0
    decimals: int = 3
    tooltip: str = ""


SCHEMA: dict[str, dict[str, ParamSpec]] = {
    "Backtracking": {
        "max_iterations": ParamSpec("Iterații maxime", "int", 1_000_000, 1, 2_000_000_000),
        "time_limit_seconds": ParamSpec("Timp maxim (s)", "float", 30.0, 0.1, 3600.0, 0.5, 1),
        "force": ParamSpec(
            "Forțează pentru n > 13 (ATENȚIE: O(n!))",
            "bool",
            False,
            tooltip=(
                "Backtracking este exact dar exponențial. Peste 13 orașe poate "
                "rula ore/zile fără să termine. Bifează doar dacă vrei să "
                "explorezi cu limita de timp ca safety net."
            ),
        ),
    },
    "Hill Climbing": {
        "max_iterations": ParamSpec("Iterații maxime", "int", 5000, 1, 1_000_000),
        "restarts": ParamSpec("Număr restart-uri", "int", 5, 1, 1000),
        "nn_start": ParamSpec("Pornire de la Nearest Neighbor", "bool", True),
    },
    "Simulated Annealing": {
        "max_iterations": ParamSpec("Iterații maxime", "int", 100_000, 100, 10_000_000),
        "initial_temp": ParamSpec("Temperatură inițială (0 = auto)", "float", 0.0, 0.0, 1e6, 1.0, 2),
        "final_temp": ParamSpec("Temperatură finală", "float", 0.001, 1e-6, 100.0, 0.001, 6),
        "cooling_rate": ParamSpec("Rata de răcire", "float", 0.995, 0.8, 0.9999, 0.001, 4),
    },
    "Genetic Algorithm": {
        "generations": ParamSpec("Generații", "int", 500, 10, 100_000),
        "population_size": ParamSpec("Mărime populație", "int", 100, 4, 5000),
        "crossover_rate": ParamSpec("Probabilitate crossover", "float", 0.9, 0.0, 1.0, 0.05, 2),
        "mutation_rate": ParamSpec("Probabilitate mutație", "float", 0.2, 0.0, 1.0, 0.05, 2),
        "elite_count": ParamSpec("Elite count", "int", 5, 0, 1000),
        "tournament_k": ParamSpec("Mărime turneu", "int", 5, 2, 100),
    },
    "Ant Colony Optimization": {
        "iterations": ParamSpec("Iterații", "int", 200, 10, 100_000),
        "num_ants": ParamSpec("Număr furnici (0 = n)", "int", 0, 0, 10_000),
        "alpha": ParamSpec("α (importanță feromon)", "float", 1.0, 0.0, 10.0, 0.1, 2),
        "beta": ParamSpec("β (importanță vizibilitate)", "float", 3.0, 0.0, 20.0, 0.1, 2),
        "evaporation": ParamSpec("Rată evaporare ρ", "float", 0.1, 0.001, 0.99, 0.01, 3),
        "Q": ParamSpec("Constantă depunere Q", "float", 100.0, 0.01, 10000.0, 1.0, 2),
    },
    "Nearest Neighbor": {
        "start_city": ParamSpec("Oraș de pornire (id)", "int", 0, 0, 100_000),
    },
}


class ParameterPanel(QWidget):
    """Panou de parametri care se rebuieste când se schimbă algoritmul."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._group: QGroupBox | None = None
        self._widgets: dict[str, QWidget] = {}
        self._current_algorithm: str | None = None

    def set_algorithm(self, algorithm_name: str) -> None:
        """Construiește dinamic câmpurile pentru algoritmul cerut."""
        self._current_algorithm = algorithm_name
        self._clear()

        params = SCHEMA.get(algorithm_name, {})
        group = QGroupBox(f"Parametri — {algorithm_name}")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        if not params:
            form.addRow(QLabel("Acest algoritm nu are parametri configurabili."))
        else:
            for key, spec in params.items():
                widget = self._build_widget(spec)
                if spec.tooltip:
                    widget.setToolTip(spec.tooltip)
                form.addRow(QLabel(spec.label), widget)
                self._widgets[key] = widget

        self._layout.addWidget(group)
        self._group = group

    def get_values(self) -> dict[str, Any]:
        """Returnează valorile curente ale parametrilor."""
        values: dict[str, Any] = {}
        if self._current_algorithm is None:
            return values
        for key, spec in SCHEMA[self._current_algorithm].items():
            widget = self._widgets.get(key)
            if widget is None:
                continue
            if spec.kind == "int":
                values[key] = widget.value()
            elif spec.kind == "float":
                v = widget.value()
                if v == 0.0 and "auto" in spec.label.lower():
                    continue
                values[key] = v
            elif spec.kind == "bool":
                values[key] = widget.isChecked()
        return values

    def _build_widget(self, spec: ParamSpec) -> QWidget:
        if spec.kind == "int":
            w = QSpinBox()
            w.setRange(int(spec.minimum), int(spec.maximum))
            w.setValue(int(spec.default))
            w.setSingleStep(int(spec.step))
            return w
        if spec.kind == "float":
            w = QDoubleSpinBox()
            w.setRange(spec.minimum, spec.maximum)
            w.setValue(float(spec.default))
            w.setSingleStep(spec.step)
            w.setDecimals(spec.decimals)
            return w
        if spec.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(spec.default))
            return w
        raise ValueError(f"Tip de parametru necunoscut: {spec.kind}")

    def _clear(self) -> None:
        if self._group is not None:
            self._layout.removeWidget(self._group)
            self._group.deleteLater()
            self._group = None
        self._widgets.clear()
