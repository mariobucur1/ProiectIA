"""
Script CLI de benchmark — rulează toți algoritmii pe toate seturile de date
și exportă un CSV + grafice comparative.

Folosire:
    cd D:\\ProiectIA\\tsp-app
    python scripts/benchmark.py --output ../results/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.algorithms import ALGORITHMS, AlgorithmConfig  # noqa: E402
from src.io import (  # noqa: E402
    export_history_plot,
    export_result_to_csv,
    load_cities_from_csv,
    load_cities_from_json,
)


def collect_datasets(data_dir: Path):
    """Încarcă automat toate seturile CSV/JSON din data_dir."""
    problems = []
    for path in sorted(data_dir.iterdir()):
        if path.suffix.lower() == ".csv":
            problems.append((path.stem, load_cities_from_csv(path)))
        elif path.suffix.lower() == ".json":
            problems.append((path.stem, load_cities_from_json(path)))
    return problems


def benchmark(problems, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for ds_name, problem in problems:
        print(f"\n=== Set: {ds_name} ({problem.n} orașe) ===")
        results = []
        for algo_name, AlgoClass in ALGORITHMS.items():
            if algo_name == "Backtracking" and problem.n > 12:
                print(f"  ⏭  {algo_name}: skip (n={problem.n} prea mare)")
                continue
            cfg = AlgorithmConfig(max_iterations=500, seed=42)
            cfg.extra = {
                "generations": 200,
                "iterations": 100,
                "restarts": 3,
            }
            try:
                result = AlgoClass(cfg).solve(problem)
                print(
                    f"  ✓ {algo_name}: lungime={result.best_length:.2f}, "
                    f"timp={result.elapsed_seconds:.3f}s"
                )
                results.append(result)
            except Exception as exc:
                print(f"  ✗ {algo_name}: {exc}")

        if results:
            export_result_to_csv(results, output_dir / f"{ds_name}_results.csv")
            export_history_plot(
                results,
                output_dir / f"{ds_name}_convergence.png",
                title=f"Convergență — {ds_name}",
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data",
                        help="Folder cu seturile de date.")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "results",
                        help="Folder pentru rezultate.")
    args = parser.parse_args()

    problems = collect_datasets(args.data)
    if not problems:
        print(f"Niciun set de date găsit în {args.data}", file=sys.stderr)
        return 1
    benchmark(problems, args.output)
    print(f"\n✓ Rezultate salvate în {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
