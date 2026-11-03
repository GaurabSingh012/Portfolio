
import pytest

from app.chunking import chunk_text, normalize_text


def test_normalize_text():
    """Normalizes line endings and unnecessary whitespace."""

    text = "Hello  \r\nWorld \t\r\n\r\n\r\nAgain  "

    result = normalize_text(text)

    assert result == "Hello\nWorld\n\nAgain"


def test_chunk_text_returns_empty_list_for_empty_input():
    """Empty or whitespace-only input produces no chunks."""

    assert chunk_text("") == []
    assert chunk_text("   \n\t  ") == []


def test_chunk_text_keeps_short_text_as_single_chunk():
    """Text shorter than chunk_size should remain one chunk."""

    text = "A short portfolio note."

    result = chunk_text(
        text,
        chunk_size=100,
        overlap=20,
    )

    assert result == [text]


def test_chunk_text_prefers_paragraph_boundary():
    """Paragraph breaks should be preferred when available."""

    text = "A" * 12 + "\n\n" + "B" * 30

    result = chunk_text(
        text,
        chunk_size=20,
        overlap=0,
    )

    assert result[0] == "A" * 12
    assert result[1].startswith("B")


def test_chunk_text_preserves_overlap():
    """Consecutive chunks should share the requested overlap."""

    # No whitespace ensures the overlap fallback is deterministic.
    text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 3

    result = chunk_text(
        text,
        chunk_size=20,
        overlap=5,
    )

    assert len(result) > 1
    assert result[0][-5:] == result[1][:5]

    # Every chunk must respect the configured maximum size.
    assert all(len(chunk) <= 20 for chunk in result)


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (-1, 0),
    ],
)
def test_chunk_text_rejects_invalid_chunk_size(
    chunk_size,
    overlap,
):
    """Chunk size must be greater than zero."""

    with pytest.raises(ValueError):
        chunk_text(
            "Some sample text",
            chunk_size=chunk_size,
            overlap=overlap,
        )


def test_chunk_text_rejects_negative_overlap():
    """Overlap cannot be negative."""

    with pytest.raises(ValueError):
        chunk_text(
            "Some sample text",
            chunk_size=100,
            overlap=-1,
        )


def test_chunk_text_rejects_overlap_equal_to_chunk_size():
    """Overlap must always be smaller than chunk_size."""

    with pytest.raises(ValueError):
        chunk_text(
            "Some sample text",
            chunk_size=100,
            overlap=100,
        )
