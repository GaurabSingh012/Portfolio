
from types import SimpleNamespace

import pytest

from app import retrieval


class FakeGeminiClient:
    def __init__(self):
        self.closed = False

        self.models = SimpleNamespace(
            embed_content=self.embed_content
        )

    def embed_content(self, **kwargs):
        dimensions = retrieval.EMBEDDING_DIMENSIONS

        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(
                    values=[0.1] * dimensions
                )
            ]
        )

    def close(self):
        self.closed = True


class FakeQdrantClient:
    def __init__(self, collection_exists=True):
        self.collection_exists_result = collection_exists
        self.closed = False
        self.query_calls = []

    def collection_exists(self, collection_name):
        return self.collection_exists_result

    def query_points(self, **kwargs):
        self.query_calls.append(kwargs)

        return SimpleNamespace(
            points=["mock-retrieved-point"]
        )

    def close(self):
        self.closed = True


def configure_clients(monkeypatch, collection_exists=True):
    """Replace Gemini and Qdrant with test clients."""

    gemini_client = FakeGeminiClient()

    qdrant_client = FakeQdrantClient(
        collection_exists=collection_exists
    )

    qdrant_arguments = {}

    def fake_qdrant_client(**kwargs):
        qdrant_arguments.update(kwargs)
        return qdrant_client

    monkeypatch.setattr(
        retrieval.genai,
        "Client",
        lambda **kwargs: gemini_client,
    )

    monkeypatch.setattr(
        retrieval,
        "QdrantClient",
        fake_qdrant_client,
    )

    monkeypatch.setattr(
        retrieval,
        "QDRANT_URL",
        "https://test-qdrant.example",
    )

    monkeypatch.setattr(
        retrieval,
        "QDRANT_API_KEY",
        "test-qdrant-key",
    )

    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "test-gemini-key",
    )

    return gemini_client, qdrant_client, qdrant_arguments


def test_retrieve_rejects_empty_question():
    """An empty question must not trigger API requests."""

    with pytest.raises(
        ValueError,
        match="question cannot be empty",
    ):
        retrieval.retrieve("   ")


@pytest.mark.parametrize("limit", [0, -1])
def test_retrieve_rejects_invalid_limit(limit):
    """The retrieval limit must be at least one."""

    with pytest.raises(
        ValueError,
        match="result limit must be at least 1",
    ):
        retrieval.retrieve("What are Gaurab's skills?", limit)


def test_retrieve_requires_gemini_api_key(monkeypatch):
    """Retrieval must fail clearly when Gemini credentials are missing."""

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(
        RuntimeError,
        match="GEMINI_API_KEY",
    ):
        retrieval.retrieve("What are Gaurab's skills?")


def test_retrieve_queries_qdrant_cloud(monkeypatch):
    """A valid question should be embedded and searched in Qdrant."""

    gemini, qdrant, arguments = configure_clients(monkeypatch)

    results = retrieval.retrieve(
        "Which model did Gaurab use for his AMR project?",
        limit=5,
    )

    assert results == ["mock-retrieved-point"]

    # Verify that cloud authentication was supplied.
    assert arguments["api_key"] == "test-qdrant-key"
    assert arguments["url"] == "https://test-qdrant.example"

    # Verify the expected collection and retrieval limit.
    query_call = qdrant.query_calls[0]

    assert query_call["collection_name"] == (
        retrieval.QDRANT_COLLECTION
    )
    assert query_call["limit"] == 5
    assert len(query_call["query"]) == retrieval.EMBEDDING_DIMENSIONS

    # Both external clients should be closed.
    assert gemini.closed
    assert qdrant.closed


def test_retrieve_fails_when_collection_is_missing(monkeypatch):
    """Missing collections should produce a clear error."""

    gemini, qdrant, _ = configure_clients(
        monkeypatch,
        collection_exists=False,
    )

    with pytest.raises(
        RuntimeError,
        match="does not exist",
    ):
        retrieval.retrieve("What are Gaurab's skills?")

    # Cleanup should happen even when retrieval fails.
    assert gemini.closed
    assert qdrant.closed

    # No vector search should occur.
    assert qdrant.query_calls == []
