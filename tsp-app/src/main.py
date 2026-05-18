"""
Entry point pentru aplicația TSP.

Rulează:
    cd D:\\ProiectIA\\tsp-app
    python -m src.main
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from .gui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("TSP Solver")
    app.setOrganizationName("USV - Proiect IA")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
