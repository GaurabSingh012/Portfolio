def normalize_text(text: str) -> str:
    """Normalize line endings and unnecessary whitespace."""
    import re

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
    """
    Find a suitable end position using this priority:
    paragraph -> line -> sentence -> word -> hard limit.

    Returns an end position suitable for text[start:end].
    """

    # 1. Prefer a paragraph break (two newline characters).
    position = text.rfind("\n\n", start, hard_end)

    if position >= minimum_boundary:
        return position + len("\n\n")

    # 2. If there is no suitable paragraph break, try a line break.
    position = text.rfind("\n", start, hard_end)

    if position >= minimum_boundary:
        return position + len("\n")

    # 3. If there is no suitable line break, try a sentence ending.
    sentence_separators = (". ", "? ", "! ")

    sentence_candidates = []

    for separator in sentence_separators:
        position = text.rfind(separator, start, hard_end)

        if position >= minimum_boundary:
            sentence_candidates.append(
                (position, len(separator))
            )

    if sentence_candidates:
        # Among sentence endings, choose the rightmost one.
        position, separator_length = max(
            sentence_candidates,
            key=lambda candidate: candidate[0],
        )

        return position + separator_length

    # 4. If there is no suitable sentence ending, try a word boundary.
    position = text.rfind(" ", start, hard_end)

    if position >= minimum_boundary:
        return position + 1

    # 5. No suitable separator was found. Use the hard limit.
    return hard_end


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 180,
) -> list[str]:
    """
    Split text into overlapping, boundary-aware character chunks.

    chunk_size: maximum target length of each chunk, in characters.
    overlap: approximate number of characters repeated between chunks.
    """

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
        # The chunk should not exceed this target end position.
        hard_end = min(start + chunk_size, text_length)

        # If the remaining text fits, use all of it as the final chunk.
        if hard_end == text_length:
            end = text_length
        else:
            # Avoid choosing a boundary too early in the chunk.
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

        # Begin the next chunk before the previous one ended.
        # This repeats approximately `overlap` characters.
        start = max(start + 1, end - overlap)

    return chunks