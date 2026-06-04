"""
Integrare LLM (Google AI Studio / Gemini) pentru aplicația TSP.

Expune:
- `load_llm_config()` — încarcă cheia API și modelul din mediu sau fișier local.
- `GeminiClient` — client REST minimal pentru API-ul Gemini.
- `GeminiError` — excepția ridicată la erori de comunicare/API.
- funcții din `analyst` pentru a construi prompt-uri de analiză a performanței.
"""

from .config import LLMConfig, load_llm_config
from .gemini_client import GeminiClient, GeminiError
from .analyst import (
    SYSTEM_PROMPT,
    build_analysis_messages,
    build_question_messages,
    summarize_results,
)

__all__ = [
    "LLMConfig",
    "load_llm_config",
    "GeminiClient",
    "GeminiError",
    "SYSTEM_PROMPT",
    "build_analysis_messages",
    "build_question_messages",
    "summarize_results",
]
