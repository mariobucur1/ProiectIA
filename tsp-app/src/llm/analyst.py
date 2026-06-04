"""
Construirea prompt-urilor pentru asistentul AI: analiză de performanță și Q&A.

Aici se transformă rezultatele algoritmilor (`AlgorithmResult`) și instanța
problemei (`TSPProblem`) într-un context text compact pe care LLM-ul îl poate
analiza pentru a oferi observații și sugestii de îmbunătățire.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # doar pentru type hints, evită importuri la runtime
    from ..core import AlgorithmResult, TSPProblem


SYSTEM_PROMPT = (
    "Ești un asistent expert în inteligență artificială și optimizare, integrat "
    "într-o aplicație didactică pentru problema Comis-Voiajorului (TSP). "
    "Cunoști în detaliu algoritmii: Backtracking, Hill Climbing, Simulated "
    "Annealing, Algoritm Genetic, Ant Colony Optimization și Nearest Neighbor. "
    "Răspunzi MEREU în limba română, clar și concis, folosind Markdown "
    "(titluri scurte, liste, **accentuări**). Când analizezi performanța, oferă "
    "observații concrete legate de datele primite și sugestii practice de "
    "îmbunătățire a parametrilor sau de alegere a algoritmului. Evită răspunsurile "
    "generice — raportează-te la cifrele furnizate. Nu inventa rezultate."
)


def _problem_block(problem: Optional["TSPProblem"]) -> str:
    if problem is None:
        return "Set de date: (niciun set încărcat momentan)."
    return f"Set de date: „{problem.name}\" cu {problem.n} orașe."


def summarize_results(
    results: list["AlgorithmResult"],
    problem: Optional["TSPProblem"] = None,
) -> str:
    """
    Rezumă într-un tabel text rezultatele rulărilor, marcând cel mai bun.

    Folosit atât în prompt-ul de analiză, cât și ca preview în UI.
    """
    lines = [_problem_block(problem), ""]

    if not results:
        lines.append("Nu există încă rulări de algoritmi.")
        return "\n".join(lines)

    best = min(results, key=lambda r: r.best_length)
    lines.append("Rezultate rulări (algoritm | lungime | timp | iterații):")
    for r in results:
        marker = "  <- cel mai bun" if r is best else ""
        gap = ""
        if best.best_length > 0:
            gap_pct = (r.best_length - best.best_length) / best.best_length * 100.0
            gap = f" | gap +{gap_pct:.1f}%" if gap_pct > 1e-9 else " | gap 0.0%"
        lines.append(
            f"- {r.algorithm_name}: lungime {r.best_length:.2f} | "
            f"timp {r.elapsed_seconds:.3f}s | {r.iterations} iter{gap}{marker}"
        )

    # câteva detalii de convergență pentru cel mai bun
    if best.convergence_history:
        hist = best.convergence_history
        lines.append("")
        lines.append(
            f"Convergența celui mai bun ({best.algorithm_name}): "
            f"start {hist[0]:.2f} → final {hist[-1]:.2f} "
            f"în {len(hist)} pași înregistrați."
        )
    return "\n".join(lines)


def build_analysis_messages(
    results: list["AlgorithmResult"],
    problem: Optional["TSPProblem"] = None,
) -> tuple[str, list[dict]]:
    """
    Construiește (system_prompt, messages) pentru o cerere de analiză a performanței.
    """
    context = summarize_results(results, problem)
    user_text = (
        "Analizează performanța algoritmilor de mai jos pentru această instanță TSP. "
        "Structurează răspunsul astfel:\n"
        "1. **Câștigător** — ce algoritm a dat cel mai bun raport calitate/timp și de ce.\n"
        "2. **Observații** — ce arată diferențele de lungime și timp.\n"
        "3. **Sugestii** — ajustări concrete de parametri sau alt algoritm de încercat, "
        "ținând cont de numărul de orașe.\n\n"
        f"Date:\n{context}"
    )
    return SYSTEM_PROMPT, [{"role": "user", "text": user_text}]


def build_question_messages(
    question: str,
    results: Optional[list["AlgorithmResult"]] = None,
    problem: Optional["TSPProblem"] = None,
    current_algorithm: Optional[str] = None,
) -> tuple[str, list[dict]]:
    """
    Construiește (system_prompt, messages) pentru o întrebare liberă a utilizatorului,
    atașând contextul curent (set de date, algoritm selectat, rezultate) dacă există.
    """
    context_parts = [_problem_block(problem)]
    if current_algorithm:
        context_parts.append(f"Algoritm selectat în interfață: {current_algorithm}.")
    if results:
        context_parts.append("")
        context_parts.append(summarize_results(results, problem))

    context = "\n".join(context_parts)
    user_text = f"Context curent al aplicației:\n{context}\n\nÎntrebare: {question.strip()}"
    return SYSTEM_PROMPT, [{"role": "user", "text": user_text}]
