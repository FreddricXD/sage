from app.rag.chunk import chunk_text


def test_chunk_splits_long_text_with_overlap():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text([(0, text)], chunk_size=200, overlap=40)

    assert len(chunks) > 1
    # Chunks should be indexed sequentially.
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # Each chunk should respect the size budget (allowing one word of slack).
    for c in chunks:
        assert len(c.content) <= 200 + 20


def test_chunk_preserves_page_numbers():
    chunks = chunk_text([(3, "hello world from page three")], chunk_size=100, overlap=10)
    assert chunks
    assert all(c.page == 3 for c in chunks)


def test_chunk_skips_empty_pages():
    chunks = chunk_text([(1, "   "), (2, "real content here")], chunk_size=100, overlap=10)
    assert all(c.page == 2 for c in chunks)


def test_overlap_clamped_when_too_large():
    text = " ".join(f"w{i}" for i in range(100))
    # overlap >= chunk_size should not cause an infinite loop / crash
    chunks = chunk_text([(0, text)], chunk_size=50, overlap=80)
    assert len(chunks) >= 1
