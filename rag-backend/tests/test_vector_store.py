
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import vector_store as vs
from app.ingestion import Document


# ---------------------------------------------------------
# Mock clients
# ---------------------------------------------------------

class FakeGeminiClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeQdrantClient:
    def __init__(self):
        self.upsert_calls = []
        self.closed = False

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def close(self):
        self.closed = True


# ---------------------------------------------------------
# Shared test configuration
# ---------------------------------------------------------

def configure_sync(
    monkeypatch,
    tmp_path,
    paths,
    documents,
    existing_by_source,
):
    """Replace external services and repository access with mocks."""

    gemini_client = FakeGeminiClient()
    qdrant_client = FakeQdrantClient()
    deleted_ids = []

    monkeypatch.setattr(vs, "ROOT_DIR", tmp_path)

    monkeypatch.setattr(
        vs,
        "discover_documents",
        lambda: paths,
    )

    monkeypatch.setattr(
        vs,
        "load_documents",
        lambda paths: documents,
    )

    monkeypatch.setattr(
        vs,
        "QDRANT_URL",
        "https://test-qdrant.example",
    )

    monkeypatch.setattr(
        vs,
        "QDRANT_API_KEY",
        "test-api-key",
    )

    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "test-gemini-key",
    )

    monkeypatch.setattr(
        vs.genai,
        "Client",
        lambda **kwargs: gemini_client,
    )

    monkeypatch.setattr(
        vs,
        "QdrantClient",
        lambda **kwargs: qdrant_client,
    )

    monkeypatch.setattr(
        vs,
        "ensure_collection",
        lambda client: None,
    )

    monkeypatch.setattr(
        vs,
        "load_existing_points",
        lambda client: existing_by_source,
    )

    def fake_delete(client, point_ids):
        if point_ids:
            deleted_ids.append(set(point_ids))

    monkeypatch.setattr(
        vs,
        "delete_point_ids",
        fake_delete,
    )

    return gemini_client, qdrant_client, deleted_ids


def create_document(tmp_path, text):
    """Create a temporary document and its ingestion metadata."""

    path = tmp_path / "knowledge" / "profile.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    document = Document(
        source="knowledge/profile.md",
        title="profile",
        text=text,
    )

    return path, document


def create_old_point(point_id, content_hash):
    """Create a mock existing Qdrant point."""

    return SimpleNamespace(
        id=point_id,
        payload={
            "source": "knowledge/profile.md",
            "title": "profile",
            "chunk_index": 0,
            "content_hash": content_hash,
            "pipeline_version": vs.PIPELINE_VERSION,
            "embedding_model": vs.EMBEDDING_MODEL,
            "embedding_dimensions": vs.EMBEDDING_DIMENSIONS,
        },
    )


# ---------------------------------------------------------
# 1. Unchanged documents
# ---------------------------------------------------------

def test_sync_skips_unchanged_document(
    monkeypatch,
    tmp_path,
):
    """Unchanged documents should not generate embeddings again."""

    text = "Gaurab is an AI and ML student."

    path, document = create_document(tmp_path, text)

    normalized = vs.normalize_text(text)
    fingerprint = vs.content_hash(normalized)

    old_point = create_old_point(
        "existing-point",
        fingerprint,
    )

    gemini, qdrant, deleted = configure_sync(
        monkeypatch,
        tmp_path,
        [path],
        [document],
        {"knowledge/profile.md": [old_point]},
    )

    def unexpected_embedding(*args, **kwargs):
        pytest.fail("Unchanged document should not be embedded.")

    monkeypatch.setattr(
        vs,
        "embed_chunks",
        unexpected_embedding,
    )

    vs.sync_to_qdrant()

    assert qdrant.upsert_calls == []
    assert deleted == []
    assert gemini.closed
    assert qdrant.closed


# ---------------------------------------------------------
# 2. Modified documents
# ---------------------------------------------------------

def test_sync_updates_modified_document(
    monkeypatch,
    tmp_path,
):
    """Modified content should be embedded and uploaded."""

    text = "Gaurab is an AI and ML engineer."

    path, document = create_document(tmp_path, text)

    old_point = create_old_point(
        "old-point",
        "outdated-content-hash",
    )

    _, qdrant, deleted = configure_sync(
        monkeypatch,
        tmp_path,
        [path],
        [document],
        {"knowledge/profile.md": [old_point]},
    )

    monkeypatch.setattr(
        vs,
        "embed_chunks",
        lambda client, title, chunks: [
            [0.1] * vs.EMBEDDING_DIMENSIONS
            for _ in chunks
        ],
    )

    vs.sync_to_qdrant()

    assert len(qdrant.upsert_calls) == 1

    uploaded_points = qdrant.upsert_calls[0]["points"]

    assert len(uploaded_points) == len(vs.chunk_text(
        vs.normalize_text(text)
    ))

    assert uploaded_points[0].payload["content_hash"] == (
        vs.content_hash(vs.normalize_text(text))
    )

    assert deleted == [{"old-point"}]


# ---------------------------------------------------------
# 3. Deleted documents
# ---------------------------------------------------------

def test_sync_removes_deleted_document(
    monkeypatch,
    tmp_path,
):
    """Points belonging to deleted documents should be removed."""

    old_point = create_old_point(
        "deleted-document-point",
        "old-hash",
    )

    _, qdrant, deleted = configure_sync(
        monkeypatch,
        tmp_path,
        [],
        [],
        {"knowledge/profile.md": [old_point]},
    )

    vs.sync_to_qdrant()

    assert deleted == [{"deleted-document-point"}]
    assert qdrant.upsert_calls == []


# ---------------------------------------------------------
# 4. Unreadable documents
# ---------------------------------------------------------

def test_sync_preserves_points_for_unreadable_document(
    monkeypatch,
    tmp_path,
):
    """An unreadable but still discovered file must not be deleted."""

    path, _ = create_document(
        tmp_path,
        "Existing profile information.",
    )

    old_point = create_old_point(
        "existing-point",
        "old-hash",
    )

    # The path is discovered, but load_documents could not extract it.
    _, qdrant, deleted = configure_sync(
        monkeypatch,
        tmp_path,
        [path],
        [],
        {"knowledge/profile.md": [old_point]},
    )

    vs.sync_to_qdrant()

    assert deleted == []
    assert qdrant.upsert_calls == []


# ---------------------------------------------------------
# 5. Embedding failures
# ---------------------------------------------------------

def test_sync_preserves_old_points_when_embedding_fails(
    monkeypatch,
    tmp_path,
):
    """Old vectors must remain when replacement embeddings fail."""

    path, document = create_document(
        tmp_path,
        "Updated profile information.",
    )

    old_point = create_old_point(
        "old-point",
        "outdated-hash",
    )

    gemini, qdrant, deleted = configure_sync(
        monkeypatch,
        tmp_path,
        [path],
        [document],
        {"knowledge/profile.md": [old_point]},
    )

    def fail_embedding(*args, **kwargs):
        raise RuntimeError("Simulated embedding failure")

    monkeypatch.setattr(
        vs,
        "embed_chunks",
        fail_embedding,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated embedding failure",
    ):
        vs.sync_to_qdrant()

    assert qdrant.upsert_calls == []
    assert deleted == []
    assert gemini.closed
    assert qdrant.closed
