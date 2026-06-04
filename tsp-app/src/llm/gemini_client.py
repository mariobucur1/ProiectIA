"""
Client REST minimal pentru API-ul Google Gemini (Google AI Studio).

Folosește `requests` (deja dependență a proiectului) — nu necesită SDK extern.
Suportă conversații multi-turn și un mesaj de sistem (system instruction).

Documentație: https://ai.google.dev/api/generate-content
"""

from __future__ import annotations

from typing import Optional

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Rolurile acceptate de API. Conversația din UI folosește "user"/"model".
_ALLOWED_ROLES = {"user", "model"}


class GeminiError(Exception):
    """Eroare la apelarea API-ului Gemini (rețea, autentificare, conținut blocat)."""


class GeminiClient:
    """
    Client subțire pentru `models/{model}:generateContent`.

    Exemplu:
        client = GeminiClient(api_key="AIza...", model="gemini-2.0-flash")
        text = client.generate(
            messages=[{"role": "user", "text": "Salut!"}],
            system="Ești un asistent util.",
        )
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite", timeout: float = 60.0):
        if not api_key:
            raise GeminiError("Cheie API lipsă. Configurează GEMINI_API_KEY sau llm_config.local.json.")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
    ) -> str:
        """
        Trimite conversația către Gemini și returnează textul răspunsului.

        `messages`: listă de dict-uri `{"role": "user"|"model", "text": str}`.
        Ridică `GeminiError` la orice problemă (rețea, status non-200, blocare).
        """
        url = f"{API_BASE}/models/{self.model}:generateContent"

        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            if role not in _ALLOWED_ROLES:
                role = "user"
            contents.append({"role": role, "parts": [{"text": msg.get("text", "")}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        try:
            resp = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise GeminiError(f"Eroare de rețea la apelarea Gemini: {exc}") from exc

        if resp.status_code != 200:
            raise GeminiError(self._format_http_error(resp))

        try:
            data = resp.json()
        except ValueError as exc:
            raise GeminiError("Răspuns invalid (nu este JSON) de la Gemini.") from exc

        return self._extract_text(data)

    def list_models(self) -> list[str]:
        """Returnează numele modelelor disponibile (utile pentru depanare)."""
        url = f"{API_BASE}/models"
        try:
            resp = requests.get(url, params={"key": self.api_key}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise GeminiError(f"Eroare de rețea la listarea modelelor: {exc}") from exc
        if resp.status_code != 200:
            raise GeminiError(self._format_http_error(resp))
        data = resp.json()
        return [m.get("name", "") for m in data.get("models", [])]

    @staticmethod
    def _format_http_error(resp: requests.Response) -> str:
        try:
            err = resp.json().get("error", {})
            message = err.get("message", resp.text)
        except ValueError:
            message = resp.text
        return f"Gemini a returnat HTTP {resp.status_code}: {message}"

    @staticmethod
    def _extract_text(data: dict) -> str:
        candidates = data.get("candidates")
        if not candidates:
            feedback = data.get("promptFeedback", {})
            reason = feedback.get("blockReason")
            if reason:
                raise GeminiError(f"Conținut blocat de Gemini (motiv: {reason}).")
            raise GeminiError("Gemini nu a returnat niciun răspuns.")

        candidate = candidates[0]
        finish = candidate.get("finishReason")
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()

        if not text:
            if finish and finish != "STOP":
                raise GeminiError(f"Răspuns gol (finishReason={finish}).")
            raise GeminiError("Gemini a returnat un răspuns gol.")
        return text
