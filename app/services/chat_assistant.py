"""Hybrid carbon-footprint chat assistant.

Answers free-text questions about carbon footprints using two tiers:

1. **Optional LLM (preferred when configured):** if an ``LLM_API_KEY``
   environment variable is present, the question is sent to an OpenAI-compatible
   chat endpoint, so Terra can answer open-ended questions. The call uses only
   the Python standard library (no extra dependency), is time-limited, and
   **falls back to the knowledge base** on any error.

2. **Knowledge base (always available, no secrets):** a TF-IDF + cosine-
   similarity retriever matches the question to the best entry in
   :data:`app.services.knowledge_base.KNOWLEDGE_BASE`. This works fully offline
   and is used whenever no API key is set, or if the LLM call fails.

No API key is ever hard-coded or committed; the key is read from the
environment (e.g. a git-ignored ``.env`` file) at request time.

Security: user input is sanitised and length-capped before use, and the system
prompt constrains the model to the carbon-footprint domain.
"""

import json
import os
import urllib.request
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.knowledge_base import KNOWLEDGE_BASE
from app.utils.security import sanitize_text

# Minimum cosine similarity for a knowledge-base answer to be confident.
_MATCH_THRESHOLD = 0.12

# Maximum characters accepted from the user (anti-DoS; questions are short).
_MAX_QUESTION_LENGTH = 500

# System prompt used when the optional LLM is enabled.
_LLM_SYSTEM_PROMPT = (
    "You are Terra, a friendly, accurate assistant that ONLY answers questions "
    "about carbon footprints, personal emissions, and practical ways to live "
    "more sustainably. Keep answers concise (2-4 sentences), factual and "
    "encouraging. If a question is unrelated to carbon or sustainability, "
    "gently say it is outside your scope."
)


class ChatAssistant:
    """Retrieval-based assistant with an optional, preferred LLM brain."""

    def __init__(self) -> None:
        self._vectorizer = None  # type: Optional[TfidfVectorizer]
        self._matrix = None

    # ------------------------------------------------------------------ #
    # Knowledge-base retrieval
    # ------------------------------------------------------------------ #
    @staticmethod
    def _document(entry: Dict[str, str]) -> str:
        """Build the searchable text for one knowledge-base entry."""
        return " ".join(
            (entry["topic"], entry["keywords"], entry["answer"])
        ).lower()

    def _ensure_index(self):
        """Fit (once) and return the TF-IDF vectoriser and document matrix."""
        if self._vectorizer is None:
            docs = [self._document(entry) for entry in KNOWLEDGE_BASE]
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            self._matrix = vectorizer.fit_transform(docs)
            self._vectorizer = vectorizer
        return self._vectorizer, self._matrix

    def _best_match(self, question: str):
        """Return ``(entry, score)`` for the closest knowledge-base entry."""
        vectorizer, matrix = self._ensure_index()
        query_vec = vectorizer.transform([question.lower()])
        scores = cosine_similarity(query_vec, matrix)[0]
        best_index = int(scores.argmax())
        return KNOWLEDGE_BASE[best_index], float(scores[best_index])

    def _kb_answer(self, question: str) -> Dict[str, object]:
        """Answer purely from the knowledge base (with a graceful fallback)."""
        entry, score = self._best_match(question)
        if score >= _MATCH_THRESHOLD:
            return {
                "reply": entry["answer"],
                "source": "knowledge_base",
                "topic": entry["topic"],
                "confidence": round(score, 3),
                "suggestions": [],
            }
        return {
            "reply": (
                "I am not fully sure about that one. I can help with topics like "
                "transport, flights, diet, home energy, recycling and "
                "offsetting. Try rephrasing, or pick a suggestion below."
            ),
            "source": "fallback",
            "topic": entry["topic"],
            "confidence": round(score, 3),
            "suggestions": self.suggested_topics(),
        }

    # ------------------------------------------------------------------ #
    # Optional LLM augmentation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _llm_enabled() -> bool:
        """True only when an API key is configured in the environment."""
        return bool(os.environ.get("LLM_API_KEY"))

    def _ask_llm(self, question: str) -> Optional[str]:
        """Query an OpenAI-compatible chat endpoint; ``None`` on any failure."""
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            return None

        url = os.environ.get(
            "LLM_API_URL", "https://api.openai.com/v1/chat/completions"
        )
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "temperature": 0.4,
            "max_tokens": 300,
        }).encode("utf-8")

        try:
            request = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
        except Exception:
            # Network error, bad key, rate limit, timeout, unexpected shape:
            # never crash the request - fall back to the knowledge base.
            return None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def suggested_topics(self, limit: int = 6) -> List[str]:
        """Return a few example topics to seed the chat UI."""
        return [entry["topic"] for entry in KNOWLEDGE_BASE[:limit]]

    def answer(self, raw_question: str) -> Dict[str, object]:
        """Answer a user question.

        When an LLM API key is configured, the LLM is tried first (so Terra can
        handle open-ended questions); the knowledge base is used as a fast,
        free fallback and whenever no key is present.

        Returns:
            A dict with ``reply`` (str), ``source`` ("llm" | "knowledge_base" |
            "fallback"), ``topic`` (str | None), ``confidence`` (float) and
            ``suggestions`` (list[str]).
        """
        question = sanitize_text(raw_question, max_length=_MAX_QUESTION_LENGTH)
        if not question:
            return {
                "reply": "Please type a question about carbon footprints.",
                "source": "fallback",
                "topic": None,
                "confidence": 0.0,
                "suggestions": self.suggested_topics(),
            }

        # Preferred path: the LLM, when a key is configured.
        if self._llm_enabled():
            llm_reply = self._ask_llm(question)
            if llm_reply:
                return {
                    "reply": llm_reply,
                    "source": "llm",
                    "topic": None,
                    "confidence": 1.0,
                    "suggestions": [],
                }

        # Default / fallback path: the built-in knowledge base.
        return self._kb_answer(question)
