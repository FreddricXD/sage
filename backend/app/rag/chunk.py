from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    page: int
    token_count: int


def _approx_tokens(text: str) -> int:
    # Cheap, dependency-free approximation (~4 chars per token) so we avoid a
    # runtime tokenizer download.
    return max(1, len(text) // 4)


def chunk_text(
    pages: list[tuple[int, str]],
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[TextChunk]:
    """Split extracted pages into overlapping, word-aware chunks.

    chunk_size and overlap are measured in characters. Splitting on word
    boundaries keeps chunks readable and avoids cutting words in half.
    """
    if overlap >= chunk_size:
        overlap = chunk_size // 4

    chunks: list[TextChunk] = []
    index = 0

    for page, text in pages:
        words = text.split()
        if not words:
            continue

        current: list[str] = []
        current_len = 0

        for word in words:
            add_len = len(word) + 1
            if current_len + add_len > chunk_size and current:
                content = " ".join(current).strip()
                chunks.append(
                    TextChunk(content, index, page, _approx_tokens(content))
                )
                index += 1

                # Build overlap tail (by characters) for the next chunk.
                if overlap > 0:
                    tail: list[str] = []
                    tail_len = 0
                    for w in reversed(current):
                        wl = len(w) + 1
                        if tail_len + wl > overlap:
                            break
                        tail.insert(0, w)
                        tail_len += wl
                    current = tail
                    current_len = tail_len
                else:
                    current = []
                    current_len = 0

            current.append(word)
            current_len += add_len

        if current:
            content = " ".join(current).strip()
            if content:
                chunks.append(
                    TextChunk(content, index, page, _approx_tokens(content))
                )
                index += 1

    return chunks
