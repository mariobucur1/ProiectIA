"""
Încărcarea configurației LLM (cheie API + model) fără a o hardcoda în sursă.

Ordinea de prioritate:
1. Variabile de mediu: GEMINI_API_KEY (sau GOOGLE_API_KEY), GEMINI_MODEL.
2. Fișier local JSON (NU este versionat în Git): `llm_config.local.json`,
   căutat în rădăcina `tsp-app/` și în directorul curent de lucru.

Fișierul local arată așa:
    {
        "api_key": "AIza...",
        "model": "gemini-2.5-flash-lite"
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_MODEL = "gemini-2.5-flash-lite"
CONFIG_FILENAME = "llm_config.local.json"

# Rădăcina pachetului tsp-app: .../tsp-app/src/llm/config.py -> parents[2] == tsp-app/
_APP_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class LLMConfig:
    """Configurația necesară pentru a vorbi cu Gemini."""

    api_key: Optional[str] = None
    model: str = DEFAULT_MODEL

    @property
    def is_ready(self) -> bool:
        return bool(self.api_key)


def _candidate_files() -> list[Path]:
    return [
        _APP_ROOT / CONFIG_FILENAME,
        Path.cwd() / CONFIG_FILENAME,
    ]


def _load_from_file() -> dict:
    for path in _candidate_files():
        if path.is_file():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    return data
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def load_llm_config() -> LLMConfig:
    """Construiește un `LLMConfig` din mediu + fișier local."""
    file_data = _load_from_file()

    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or file_data.get("api_key")
    )
    model = (
        os.environ.get("GEMINI_MODEL")
        or file_data.get("model")
        or DEFAULT_MODEL
    )

    return LLMConfig(api_key=api_key or None, model=model)
