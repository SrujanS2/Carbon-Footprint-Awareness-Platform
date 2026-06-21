"""Chat controller.

Thin orchestration layer over :class:`app.services.chat_assistant.ChatAssistant`.
A single shared assistant instance is created so the TF-IDF index is built once
and reused across requests. Contains no Flask code.
"""

from typing import Dict

from app.services.chat_assistant import ChatAssistant

# Shared instance: the retrieval index is built lazily on first use and cached.
_assistant = ChatAssistant()


def ask(message: str) -> Dict[str, object]:
    """Answer a user chat message via the shared assistant."""
    return _assistant.answer(message)


def suggestions() -> Dict[str, object]:
    """Return seed topics for the chat UI."""
    return {"suggestions": _assistant.suggested_topics()}
