"""Unit + integration tests for the hybrid chat assistant."""

import json

import pytest

from app.services.chat_assistant import ChatAssistant
from app.services.knowledge_base import KNOWLEDGE_BASE


@pytest.fixture()
def assistant():
    return ChatAssistant()


def test_knowledge_base_is_well_formed():
    assert len(KNOWLEDGE_BASE) >= 20
    for entry in KNOWLEDGE_BASE:
        assert {"topic", "keywords", "answer"} <= set(entry)
        assert entry["answer"].strip()


def test_answer_returns_expected_shape(assistant):
    result = assistant.answer("What is a carbon footprint?")
    for key in ("reply", "source", "topic", "confidence", "suggestions"):
        assert key in result
    assert isinstance(result["reply"], str) and result["reply"]


def test_confident_match_uses_knowledge_base(assistant):
    result = assistant.answer("How can I reduce emissions from flying?")
    assert result["source"] == "knowledge_base"
    assert result["confidence"] >= 0.12
    assert "flight" in result["reply"].lower() or "air" in result["reply"].lower()


@pytest.mark.parametrize("question,needle", [
    ("Tell me about electric vehicles", "electric"),
    ("Should I eat less meat?", "meat"),
    ("How do solar panels help?", "solar"),
    ("What does net zero mean?", "net zero"),
])
def test_topic_matching(assistant, question, needle):
    result = assistant.answer(question)
    assert needle.lower() in result["reply"].lower()


def test_empty_question_is_handled(assistant):
    result = assistant.answer("   ")
    assert result["source"] == "fallback"
    assert result["suggestions"]


def test_unrelated_question_falls_back(assistant, monkeypatch):
    # Ensure the optional LLM is disabled so we exercise the fallback path.
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    result = assistant.answer("zxqw qwzx nonsense token 12345")
    assert result["source"] == "fallback"
    assert result["suggestions"]


def test_input_is_sanitised(assistant):
    # A script payload must not appear verbatim; it is sanitised before use.
    result = assistant.answer("<script>alert(1)</script> what is co2e")
    assert "<script>" not in json.dumps(result)


def test_suggested_topics(assistant):
    topics = assistant.suggested_topics(limit=4)
    assert len(topics) == 4
    assert all(isinstance(t, str) for t in topics)


# --- API endpoints ---------------------------------------------------------
def test_chat_endpoint_success(client):
    resp = client.post(
        "/api/chat",
        data=json.dumps({"message": "How do I reduce my driving emissions?"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["reply"]
    assert body["source"] in {"knowledge_base", "llm", "fallback"}


def test_chat_endpoint_requires_message(client):
    resp = client.post(
        "/api/chat", data=json.dumps({"message": "  "}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_chat_suggestions_endpoint(client):
    resp = client.get("/api/chat/suggestions")
    assert resp.status_code == 200
    assert "suggestions" in resp.get_json()
