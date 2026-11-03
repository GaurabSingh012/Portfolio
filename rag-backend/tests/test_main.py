
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)


# ---------------------------------------------------------
# Mock Gemini client
# ---------------------------------------------------------

class FakeGeminiModels:
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.generate_arguments = None

    def generate_content(self, **kwargs):
        self.generate_arguments = kwargs

        if self.error is not None:
            raise self.error

        return SimpleNamespace(text=self.answer)


class FakeGeminiClient:
    def __init__(self, answer=None, error=None):
        self.models = FakeGeminiModels(
            answer=answer,
            error=error,
        )
        self.closed = False

    def close(self):
        self.closed = True


# ---------------------------------------------------------
# 1. Local greeting handling
# ---------------------------------------------------------

def test_greeting_is_handled_without_external_apis(monkeypatch):
    """Simple greetings should not call retrieval or Gemini."""

    def unexpected_retrieval(*args, **kwargs):
        raise AssertionError("Retrieval should not be called.")

    def unexpected_gemini(*args, **kwargs):
        raise AssertionError("Gemini should not be called.")

    monkeypatch.setattr(
        main,
        "retrieve",
        unexpected_retrieval,
    )

    monkeypatch.setattr(
        main.genai,
        "Client",
        unexpected_gemini,
    )

    response = client.post(
        "/chat",
        json={"question": "Good morning"},
    )

    assert response.status_code == 200

    data = response.json()

    assert "portfolio assistant" in data["answer"].lower()
    assert data["sources"] == []


# ---------------------------------------------------------
# 2. Complete RAG answer generation
# ---------------------------------------------------------

def test_chat_generates_grounded_answer(monkeypatch):
    """Portfolio questions should retrieve context and call Gemini."""

    question = "Which model did Gaurab use for his AMR project?"

    retrieved_point = SimpleNamespace(
        payload={
            "source": "knowledge/projects/amr-command-assistant.md",
            "title": "amr-command-assistant",
            "text": "The base model was Qwen3-1.7B-Base.",
        },
        score=0.85,
    )

    monkeypatch.setattr(
        main,
        "retrieve",
        lambda question, limit: [retrieved_point],
    )

    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "test-gemini-key",
    )

    fake_client = FakeGeminiClient(
        answer="Gaurab used Qwen3-1.7B-Base."
    )

    monkeypatch.setattr(
        main.genai,
        "Client",
        lambda **kwargs: fake_client,
    )

    response = client.post(
        "/chat",
        json={"question": question},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == "Gaurab used Qwen3-1.7B-Base."
    assert len(data["sources"]) == 1

    assert (
        data["sources"][0]["source"]
        == "knowledge/projects/amr-command-assistant.md"
    )

    arguments = fake_client.models.generate_arguments

    assert "Qwen3-1.7B-Base" in arguments["contents"]
    assert question in arguments["contents"]

    assert fake_client.closed


# ---------------------------------------------------------
# 3. No readable retrieval context
# ---------------------------------------------------------

def test_chat_does_not_call_gemini_without_context(monkeypatch):
    """Empty retrieved content should not trigger generation."""

    empty_point = SimpleNamespace(
        payload={
            "source": "knowledge/profile.md",
            "title": "profile",
            "text": "   ",
        },
        score=0.5,
    )

    monkeypatch.setattr(
        main,
        "retrieve",
        lambda question, limit: [empty_point],
    )

    def unexpected_gemini(*args, **kwargs):
        raise AssertionError(
            "Gemini should not be called without readable context."
        )

    monkeypatch.setattr(
        main.genai,
        "Client",
        unexpected_gemini,
    )

    response = client.post(
        "/chat",
        json={"question": "What are Gaurab's skills?"},
    )

    assert response.status_code == 200

    data = response.json()

    # Match the actual fallback response defined in main.py.
    assert "don't have enough information" in data["answer"].lower()
    assert data["sources"] == []


# ---------------------------------------------------------
# 4. Retrieval failure
# ---------------------------------------------------------

def test_chat_handles_retrieval_failure(monkeypatch):
    """Retrieval errors should return HTTP 502."""

    def failed_retrieval(*args, **kwargs):
        raise RuntimeError("Qdrant connection failed")

    monkeypatch.setattr(
        main,
        "retrieve",
        failed_retrieval,
    )

    response = client.post(
        "/chat",
        json={"question": "What are Gaurab's skills?"},
    )

    assert response.status_code == 502

    assert (
        "couldn't look up information"
        in response.json()["detail"].lower()
    )


# ---------------------------------------------------------
# 5. Gemini quota handling
# ---------------------------------------------------------

def test_chat_handles_gemini_quota_error(monkeypatch):
    """Gemini quota exhaustion should return HTTP 429."""

    monkeypatch.setattr(
        main,
        "retrieve",
        lambda question, limit: [
            SimpleNamespace(
                payload={
                    "source": "knowledge/profile.md",
                    "title": "profile",
                    "text": "Gaurab is an AI and ML student.",
                },
                score=0.8,
            )
        ],
    )

    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "test-gemini-key",
    )

    fake_client = FakeGeminiClient(
        error=RuntimeError(
            "429 RESOURCE_EXHAUSTED: quota exceeded"
        )
    )

    monkeypatch.setattr(
        main.genai,
        "Client",
        lambda **kwargs: fake_client,
    )

    response = client.post(
        "/chat",
        json={"question": "Tell me about Gaurab."},
    )

    assert response.status_code == 429

    assert (
        "request limit"
        in response.json()["detail"].lower()
    )

    assert fake_client.closed


# ---------------------------------------------------------
# 6. Request validation
# ---------------------------------------------------------

def test_chat_rejects_empty_question():
    """Empty questions should be rejected by request validation."""

    response = client.post(
        "/chat",
        json={"question": ""},
    )

    assert response.status_code == 422
