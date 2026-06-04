"""
Panou asistent AI — chat lateral integrat cu Google Gemini.

Permite două lucruri:
- Întrebări libere către LLM (cu contextul curent: set de date, algoritm, rezultate).
- „Analizează performanța" — trimite automat rezultatele rulărilor și primește
  observații + sugestii de îmbunătățire.

Apelurile de rețea rulează pe un QThread separat (`LLMWorker`) ca să nu blocheze UI-ul.
"""

from __future__ import annotations

import html
import re
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core import AlgorithmResult, TSPProblem
from ..llm import (
    GeminiClient,
    GeminiError,
    build_analysis_messages,
    build_question_messages,
    load_llm_config,
)
from . import theme


class LLMWorker(QThread):
    """Thread care apelează Gemini fără a bloca interfața."""

    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, client: GeminiClient, system: str, messages: list[dict], parent=None):
        super().__init__(parent)
        self._client = client
        self._system = system
        self._messages = messages

    def run(self) -> None:
        try:
            text = self._client.generate(self._messages, system=self._system)
            self.succeeded.emit(text)
        except GeminiError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover - plasă de siguranță
            self.failed.emit(f"Eroare neașteptată: {exc}")


class _ChatInput(QTextEdit):
    """Câmp de input multi-linie: Enter trimite, Shift+Enter inserează rând nou."""

    submitted = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.submitted.emit()
            return
        super().keyPressEvent(event)


class AssistantPanel(QWidget):
    """Conținutul dock-ului „Asistent AI"."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._config = load_llm_config()
        self._client: Optional[GeminiClient] = None
        self._worker: Optional[LLMWorker] = None

        # context curent al aplicației, alimentat de MainWindow
        self._results: list[AlgorithmResult] = []
        self._problem: Optional[TSPProblem] = None
        self._current_algorithm: Optional[str] = None

        # istoric conversație pentru context multi-turn către API
        self._history: list[dict] = []
        self._messages_html: list[str] = []

        self._build_ui()
        self._init_client()

    # ── construcție UI ──────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._model_label = QLabel()
        self._model_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        root.addWidget(self._model_label)

        self._conversation = QTextBrowser()
        self._conversation.setOpenExternalLinks(True)
        self._conversation.setMinimumWidth(300)
        root.addWidget(self._conversation, 1)

        self._input = _ChatInput()
        self._input.setPlaceholderText(
            "Întreabă despre algoritmi, parametri, rezultate…  (Enter = trimite, Shift+Enter = rând nou)"
        )
        self._input.setMaximumHeight(90)
        self._input.submitted.connect(self._on_send)
        root.addWidget(self._input)

        buttons = QHBoxLayout()
        self._analyze_btn = QPushButton("📊 Analizează performanța")
        self._analyze_btn.clicked.connect(self._on_analyze)
        self._send_btn = QPushButton("Trimite")
        self._send_btn.setProperty("accent", "true")
        self._send_btn.clicked.connect(self._on_send)
        self._clear_btn = QPushButton("Curăță")
        self._clear_btn.clicked.connect(self._on_clear)
        buttons.addWidget(self._analyze_btn)
        buttons.addStretch(1)
        buttons.addWidget(self._clear_btn)
        buttons.addWidget(self._send_btn)
        root.addLayout(buttons)

    def _init_client(self) -> None:
        if not self._config.is_ready:
            self._model_label.setText("⚠ Fără cheie API")
            self._append_system_notice(
                "Asistentul AI nu are o cheie API configurată.\n\n"
                "Setează variabila de mediu `GEMINI_API_KEY` sau creează fișierul "
                "`llm_config.local.json` în folderul `tsp-app/` cu conținutul:\n\n"
                "```json\n{\n  \"api_key\": \"AIza...\",\n  \"model\": \"gemini-2.5-flash-lite\"\n}\n```"
            )
            self._set_busy(True)  # dezactivează intrările
            return

        try:
            self._client = GeminiClient(self._config.api_key, model=self._config.model)
        except GeminiError as exc:
            self._model_label.setText("⚠ Configurare invalidă")
            self._append_system_notice(str(exc))
            self._set_busy(True)
            return

        self._model_label.setText(f"Model: {self._config.model}  •  Google AI Studio")
        self._append_system_notice(
            "Salut! Sunt asistentul AI al aplicației. Pune-mi întrebări despre algoritmi "
            "sau apasă butonul **Analizează performanța** după ce ai rulat câțiva algoritmi."
        )

    # ── context din MainWindow ────────────────────────────────────────────────
    def set_context(
        self,
        results: list[AlgorithmResult],
        problem: Optional[TSPProblem],
        current_algorithm: Optional[str] = None,
    ) -> None:
        self._results = list(results)
        self._problem = problem
        if current_algorithm is not None:
            self._current_algorithm = current_algorithm

    def set_current_algorithm(self, name: str) -> None:
        self._current_algorithm = name

    # ── acțiuni ───────────────────────────────────────────────────────────────
    def _on_send(self) -> None:
        if self._client is None or self._is_busy():
            return
        question = self._input.toPlainText().strip()
        if not question:
            return
        self._input.clear()
        self._append_message("user", question)

        system, ctx_messages = build_question_messages(
            question,
            results=self._results,
            problem=self._problem,
            current_algorithm=self._current_algorithm,
        )
        # construim conversația: contextul + istoricul anterior + întrebarea curentă
        self._history.append({"role": "user", "text": ctx_messages[0]["text"]})
        self._start_worker(system, list(self._history))

    def _on_analyze(self) -> None:
        if self._client is None or self._is_busy():
            return
        if not self._results:
            self._append_system_notice(
                "Nu există încă rezultate de analizat. Rulează întâi unul sau mai mulți algoritmi."
            )
            return
        self._append_message(
            "user",
            "📊 Analizează performanța algoritmilor rulați pe setul de date curent.",
        )
        system, messages = build_analysis_messages(self._results, self._problem)
        self._history.append({"role": "user", "text": messages[0]["text"]})
        self._start_worker(system, list(self._history))

    def _on_clear(self) -> None:
        self._history.clear()
        self._messages_html.clear()
        self._render()
        self._append_system_notice("Conversație ștearsă. Contextul (date + rezultate) rămâne disponibil.")

    def _start_worker(self, system: str, messages: list[dict]) -> None:
        self._set_busy(True)
        self._append_thinking()
        self._worker = LLMWorker(self._client, system, messages, self)
        self._worker.succeeded.connect(self._on_reply)
        self._worker.failed.connect(self._on_failure)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def _on_reply(self, text: str) -> None:
        self._remove_thinking()
        self._history.append({"role": "model", "text": text})
        self._append_message("assistant", text)

    def _on_failure(self, message: str) -> None:
        self._remove_thinking()
        # nu păstrăm în istoric un turn fără răspuns valid
        if self._history and self._history[-1]["role"] == "user":
            self._history.pop()
        self._append_system_notice(f"⚠ {message}")

    def _cleanup_worker(self) -> None:
        self._set_busy(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self._input.setFocus()

    # ── stare / busy ────────────────────────────────────────────────────────
    def _is_busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_busy(self, busy: bool) -> None:
        enabled = not busy and self._client is not None
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        self._analyze_btn.setEnabled(enabled)

    # ── randare conversație ──────────────────────────────────────────────────
    def _append_message(self, role: str, text: str) -> None:
        self._messages_html.append(_render_bubble(role, text))
        self._render()

    def _append_system_notice(self, text: str) -> None:
        self._messages_html.append(_render_bubble("system", text))
        self._render()

    def _append_thinking(self) -> None:
        self._messages_html.append(
            f'<div id="thinking" style="color:{theme.TEXT_MUTED}; font-style:italic; '
            f'margin:6px 2px;">Asistentul scrie…</div>'
        )
        self._render()

    def _remove_thinking(self) -> None:
        self._messages_html = [m for m in self._messages_html if 'id="thinking"' not in m]
        self._render()

    def _render(self) -> None:
        body = "".join(self._messages_html)
        self._conversation.setHtml(f"<body style='color:{theme.TEXT};'>{body}</body>")
        sb = self._conversation.verticalScrollBar()
        sb.setValue(sb.maximum())


# ── helpers de randare (în afara clasei, ușor de testat) ─────────────────────

def _render_bubble(role: str, text: str) -> str:
    """Returnează HTML-ul unei „bule" de mesaj în funcție de rol."""
    if role == "user":
        return (
            f'<div style="margin:8px 0;"><span style="color:{theme.ACCENT}; '
            f'font-weight:600;">Tu</span><div style="background:{theme.SURFACE}; '
            f'border:1px solid {theme.BORDER}; border-radius:8px; padding:6px 10px; '
            f'margin-top:3px;">{_md_to_html(text)}</div></div>'
        )
    if role == "assistant":
        return (
            f'<div style="margin:8px 0;"><span style="color:{theme.ACCENT}; '
            f'font-weight:600;">Asistent AI</span><div style="background:transparent; '
            f'border-left:3px solid {theme.ACCENT}; '
            f'padding:4px 10px; margin-top:3px;">{_md_to_html(text)}</div></div>'
        )
    # system
    return (
        f'<div style="margin:8px 0; color:{theme.TEXT_MUTED}; font-size:12px; '
        f'border-left:2px solid {theme.BORDER}; padding-left:8px;">{_md_to_html(text)}</div>'
    )


_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)")


def _inline_md(text: str) -> str:
    """Convertește marcajele inline (cod, bold, italic) după escape HTML."""
    out = html.escape(text)
    out = _INLINE_CODE.sub(
        lambda m: f'<code style="background:{theme.SURFACE}; padding:1px 4px; '
        f'border-radius:3px; font-family:Consolas,monospace;">{m.group(1)}</code>',
        out,
    )
    out = _BOLD.sub(r"<b>\1</b>", out)
    out = _ITALIC.sub(r"<i>\1</i>", out)
    return out


def _md_to_html(text: str) -> str:
    """
    Convertor Markdown→HTML compact pentru răspunsurile Gemini.

    Suportă: blocuri de cod ```…```, titluri #/##/###, liste (-, *, 1.),
    bold/italic/cod inline și paragrafe. Suficient pentru output-ul tipic LLM.
    """
    lines = text.split("\n")
    html_parts: list[str] = []
    in_code = False
    code_buffer: list[str] = []
    list_type: Optional[str] = None  # "ul" | "ol" | None

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            html_parts.append(f"</{list_type}>")
            list_type = None

    for raw in lines:
        line = raw.rstrip("\r")

        # blocuri de cod fenced
        if line.strip().startswith("```"):
            if in_code:
                code = html.escape("\n".join(code_buffer))
                html_parts.append(
                    f'<pre style="background:{theme.SURFACE}; border:1px solid {theme.BORDER}; '
                    f'border-radius:6px; padding:8px; overflow-x:auto; '
                    f'font-family:Consolas,monospace; font-size:12px;">{code}</pre>'
                )
                code_buffer = []
                in_code = False
            else:
                close_list()
                in_code = True
            continue

        if in_code:
            code_buffer.append(raw)
            continue

        stripped = line.strip()
        if not stripped:
            close_list()
            continue

        # titluri
        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            size = {1: 16, 2: 15, 3: 14}[level]
            html_parts.append(
                f'<div style="font-weight:700; font-size:{size}px; '
                f'color:{theme.TEXT}; margin:6px 0 2px;">{_inline_md(heading.group(2))}</div>'
            )
            continue

        # liste neordonate
        ul = re.match(r"^[-*+]\s+(.*)$", stripped)
        if ul:
            if list_type != "ul":
                close_list()
                html_parts.append("<ul style='margin:2px 0 2px 18px;'>")
                list_type = "ul"
            html_parts.append(f"<li>{_inline_md(ul.group(1))}</li>")
            continue

        # liste ordonate
        ol = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ol:
            if list_type != "ol":
                close_list()
                html_parts.append("<ol style='margin:2px 0 2px 18px;'>")
                list_type = "ol"
            html_parts.append(f"<li>{_inline_md(ol.group(1))}</li>")
            continue

        # paragraf normal
        close_list()
        html_parts.append(f'<div style="margin:3px 0;">{_inline_md(stripped)}</div>')

    if in_code and code_buffer:
        code = html.escape("\n".join(code_buffer))
        html_parts.append(
            f'<pre style="background:{theme.SURFACE}; border:1px solid {theme.BORDER}; '
            f'border-radius:6px; padding:8px; font-family:Consolas,monospace;">{code}</pre>'
        )
    close_list()
    return "".join(html_parts)
