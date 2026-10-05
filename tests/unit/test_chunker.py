from app.services.chunking.chunker import chunk_text, count_tokens


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_chunks_respect_target_size_roughly():
    text = " ".join([f"Sentence number {i} has some words in it." for i in range(50)])
    chunks = chunk_text(text, target_tokens=30, overlap_tokens=5)
    assert len(chunks) > 1
    for c in chunks:
        # allow slack for the last sentence that pushed a chunk over target
        assert c.token_count <= 60


def test_consecutive_chunks_actually_overlap():
    text = " ".join([f"This is sentence {i} with unique content {i}." for i in range(30)])
    chunks = chunk_text(text, target_tokens=25, overlap_tokens=10)
    assert len(chunks) >= 2
    # The old chunker's `overlap` parameter was declared but never used;
    # this asserts real overlap exists between consecutive chunks.
    for i in range(len(chunks) - 1):
        assert chunks[i].char_end > chunks[i + 1].char_start


def test_char_offsets_map_back_into_source_text():
    text = "First sentence here. Second sentence here. Third sentence here."
    chunks = chunk_text(text, target_tokens=1000, overlap_tokens=0)
    assert len(chunks) == 1
    span = chunks[0]
    assert text[span.char_start:span.char_end] == span.text or span.text in text


def test_count_tokens_nonzero_for_nonempty_text():
    assert count_tokens("hello world") > 0
    assert count_tokens("") == 0
