from app.rag.retrieve import (
    RetrievedChunk,
    build_context_prompt,
    reciprocal_rank_fusion,
)


def _chunk(i: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"c{i}",
        document_id=f"d{i}",
        filename=f"doc{i}.pdf",
        content=f"content number {i}",
        score=0.9,
        page=i,
    )


def test_build_context_prompt_numbers_sources():
    chunks = [_chunk(1), _chunk(2)]
    prompt = build_context_prompt(chunks, "What is the answer?")

    assert "[1] doc1.pdf (p.1)" in prompt
    assert "[2] doc2.pdf (p.2)" in prompt
    assert "Question: What is the answer?" in prompt


def test_build_context_prompt_handles_no_chunks():
    prompt = build_context_prompt([], "anything")
    assert "No context sources" in prompt
    assert "anything" in prompt


def test_rrf_rewards_agreement_across_rankers():
    vector = ["a", "b", "c"]
    text = ["b", "a", "d"]
    fused = reciprocal_rank_fusion([vector, text])
    ordered = sorted(fused, key=lambda i: fused[i], reverse=True)
    # "a" (ranks 0 and 1) and "b" (ranks 1 and 0) should beat single-list hits.
    assert set(ordered[:2]) == {"a", "b"}
    assert ordered[-1] in {"c", "d"}


def test_rrf_top_item_appears_in_both_lists():
    fused = reciprocal_rank_fusion([["x", "y", "z"], ["y", "x", "w"]])
    top = max(fused, key=lambda i: fused[i])
    assert top in {"x", "y"}
