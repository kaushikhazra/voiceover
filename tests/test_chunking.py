"""Tests for engine.split_into_chunks — chunking at sentence boundaries."""

# Heavy-dep stubs (qwen_tts, torch, soundfile) are in conftest.py.

from voiceover.engine import split_into_chunks, MAX_WORDS_PER_CHUNK


def test_single_short_sentence_is_one_chunk():
    text = "The quick brown fox jumps over the lazy dog."
    chunks = split_into_chunks(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_multiple_sentences_within_limit_stay_together():
    # Two short sentences — should be in one chunk
    text = "Hello world. This is a test."
    chunks = split_into_chunks(text)
    assert len(chunks) == 1


def test_split_at_sentence_boundary_when_over_limit():
    # Build two groups of sentences that together exceed MAX_WORDS_PER_CHUNK
    # Each group is just under the limit on its own
    half = MAX_WORDS_PER_CHUNK // 2
    sentence_a = " ".join(["word"] * half) + "."
    sentence_b = " ".join(["word"] * half) + "."
    sentence_c = " ".join(["word"] * half) + "."

    # sentence_a + sentence_b would exceed the limit
    text = f"{sentence_a} {sentence_b} {sentence_c}"
    chunks = split_into_chunks(text)

    assert len(chunks) >= 2, "Text exceeding word limit should produce multiple chunks"
    for chunk in chunks:
        # Each chunk must be at or below the word limit (unless it's a lone long sentence)
        word_count = len(chunk.split())
        assert word_count <= MAX_WORDS_PER_CHUNK, (
            f"Chunk has {word_count} words, exceeds MAX_WORDS_PER_CHUNK={MAX_WORDS_PER_CHUNK}"
        )


def test_sentence_longer_than_limit_becomes_own_chunk():
    # A single sentence with more than MAX_WORDS_PER_CHUNK words
    long_sentence = " ".join(["word"] * (MAX_WORDS_PER_CHUNK + 10)) + "."
    normal_sentence = "This is short."
    text = f"{normal_sentence} {long_sentence}"
    chunks = split_into_chunks(text)

    # The long sentence must appear as its own chunk
    long_chunks = [c for c in chunks if len(c.split()) > MAX_WORDS_PER_CHUNK]
    assert len(long_chunks) == 1


def test_empty_string_returns_one_empty_chunk():
    """Empty input produces a single-element list containing the empty string."""
    chunks = split_into_chunks("")
    assert chunks == [""]
