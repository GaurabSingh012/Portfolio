
import re


def normalize_text(text: str) -> str:
    """Normalize line endings and unnecessary whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_chunk_boundary(
    text: str,
    start: int,
    hard_end: int,
    minimum_boundary: int,
) -> int:
    """Choose paragraph, line, sentence, word, or hard boundary."""

    # 1. Prefer the rightmost acceptable paragraph break.
    position = text.rfind("\n\n", start, hard_end)

    if position >= minimum_boundary:
        return position + 2

    # 2. Otherwise, prefer the rightmost acceptable line break.
    position = text.rfind("\n", start, hard_end)

    if position >= minimum_boundary:
        return position + 1

    # 3. Otherwise, find the rightmost acceptable sentence ending.
    candidates = []

    for separator in (". ", "? ", "! "):
        position = text.rfind(separator, start, hard_end)

        if position >= minimum_boundary:
            candidates.append((position, len(separator)))

    if candidates:
        position, width = max(candidates, key=lambda item: item[0])
        return position + width

    # 4. Otherwise, prefer a word boundary.
    position = text.rfind(" ", start, hard_end)

    if position >= minimum_boundary:
        return position + 1

    # 5. No suitable separator found.
    return hard_end


def find_overlap_start(
    text: str,
    previous_start: int,
    previous_end: int,
    overlap: int,
) -> int:
    """
    Calculate the next chunk's start near the requested overlap.

    Avoid starting in the middle of a word when possible.
    The resulting overlap may vary slightly.
    """
    candidate = max(previous_start + 1, previous_end - overlap)

    if candidate >= len(text):
        return candidate

    # Already starts at a word boundary.
    if text[candidate - 1].isspace():
        return candidate

    # Prefer moving forward to finish the partial word.
    for index in range(candidate, previous_end):
        if text[index].isspace():
            return index + 1

    # If necessary, move backward to a preceding word boundary.
    for index in range(candidate - 1, previous_start - 1, -1):
        if text[index].isspace():
            return index + 1

    # Fallback for long unbroken strings.
    return candidate


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 180,
) -> list[str]:
    """Create overlapping, boundary-aware character chunks."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be >= 0 and smaller than chunk_size."
        )

    text = normalize_text(text)

    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        hard_end = min(start + chunk_size, text_length)

        if hard_end == text_length:
            end = text_length
        else:
            minimum_boundary = start + int(chunk_size * 0.6)

            end = find_chunk_boundary(
                text=text,
                start=start,
                hard_end=hard_end,
                minimum_boundary=minimum_boundary,
            )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = find_overlap_start(
            text=text,
            previous_start=start,
            previous_end=end,
            overlap=overlap,
        )

    return chunks
