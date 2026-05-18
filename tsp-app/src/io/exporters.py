"""Export rezultate: CSV + grafice de convergență pentru raportul Colab."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from ..core import AlgorithmResult


def export_result_to_csv(
    results: Sequence[AlgorithmResult],
    output_path: str | Path,
) -> Path:
    """
    Exportă rezultate comparative într-un CSV. Util pentru raportul Colab.

    Coloane: algorithm, best_length, elapsed_seconds, iterations, tour_size, extra_*.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [r.to_dict() for r in results]
    if not rows:
        raise ValueError("Nicio rezultat de exportat.")

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    return output_path


def export_history_plot(
    results: Sequence[AlgorithmResult],
    output_path: str | Path,
    title: str = "Convergență algoritmi TSP",
) -> Path:
    """
    Generează un PNG cu evoluția lungimii minime pe parcursul iterațiilor
    pentru fiecare algoritm. Necesită matplotlib.
    """
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    for r in results:
        if not r.convergence_history:
            continue
        ax.plot(r.convergence_history, label=f"{r.algorithm_name} ({r.best_length:.1f})")

    ax.set_xlabel("Iterație")
    ax.set_ylabel("Lungime tur")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return output_path
