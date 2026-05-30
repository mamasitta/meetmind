from app.rag.chunker import (
    chunk_transcript,
    build_smart_chunks,
    get_smart_overlap,
    get_last_sentence,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


class TestChunkTranscript:

    def test_short_transcript_stays_one_chunk(self):
        transcript = "Alice: Hi\nBob: Hello"
        chunks = chunk_transcript(transcript)
        assert len(chunks) == 1

    def test_returns_list(self):
        transcript = "Alice: Hello everyone"
        chunks = chunk_transcript(transcript)
        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_empty_transcript_handled(self):
        # should not crash — returns original
        chunks = chunk_transcript("")
        assert isinstance(chunks, list)

    def test_long_transcript_splits_into_multiple(self):
        # create a transcript clearly over CHUNK_SIZE
        long_text = "Alice: " + ("This is a long sentence about the project. " * 50)
        chunks = chunk_transcript(long_text)
        assert len(chunks) > 1

    def test_chunks_are_strings(self):
        transcript = "Alice: Hello\nBob: Hi\nAlice: Goodbye"
        chunks = chunk_transcript(transcript)
        assert all(isinstance(c, str) for c in chunks)

    def test_speaker_preserved_in_chunks(self):
        # speaker names should appear in chunks
        transcript = "Alice: Hello everyone\nBob: Hi Alice"
        chunks = chunk_transcript(transcript)
        combined = " ".join(chunks)
        assert "Alice" in combined
        assert "Bob" in combined

    def test_bracket_format_chunked_with_timestamps(self):
        transcript = "[00:00] Alice: Hello\n[00:05] Bob: Hi there"
        chunks = chunk_transcript(transcript)
        # timestamps should be preserved in output
        combined = " ".join(chunks)
        assert "00:00" in combined or "00:05" in combined

    def test_no_chunk_exceeds_chunk_size_significantly(self):
        # chunks should not be massively over the limit
        # some overflow is ok due to sentence-boundary splitting
        long_transcript = "\n".join([
            f"Alice: {'Word ' * 30}. This is sentence number {i}."
            for i in range(20)
        ])
        chunks = chunk_transcript(long_transcript)
        for chunk in chunks:
            # allow 2x for edge cases but nothing extreme
            assert len(chunk) < CHUNK_SIZE * 2


class TestBuildSmartChunks:

    def test_complete_turns_not_split(self):
        # a single short turn should appear complete in one chunk
        turns = [
            {"speaker": "Alice", "text": "Hello everyone."},
            {"speaker": "Bob", "text": "Hi there."},
        ]
        chunks = build_smart_chunks(turns, include_timestamp=False)
        assert len(chunks) >= 1
        # both speakers should appear
        combined = " ".join(chunks)
        assert "Alice" in combined
        assert "Bob" in combined

    def test_timestamp_included_when_present(self):
        turns = [
            {"speaker": "Alice", "text": "Hello", "timestamp": "00:05"}
        ]
        chunks = build_smart_chunks(turns, include_timestamp=True)
        assert "00:05" in chunks[0]

    def test_timestamp_excluded_when_flag_false(self):
        turns = [
            {"speaker": "Alice", "text": "Hello", "timestamp": "00:05"}
        ]
        chunks = build_smart_chunks(turns, include_timestamp=False)
        assert "00:05" not in chunks[0]

    def test_empty_turns_returns_empty(self):
        chunks = build_smart_chunks([], include_timestamp=False)
        assert chunks == []


class TestGetSmartOverlap:

    def test_returns_string(self):
        chunk = ["Alice: Hello", "Bob: Hi there"]
        result = get_smart_overlap(chunk, CHUNK_OVERLAP)
        assert isinstance(result, str)

    def test_small_chunk_returns_whole(self):
        chunk = ["Alice: Hi"]
        result = get_smart_overlap(chunk, CHUNK_OVERLAP)
        assert "Alice" in result

    def test_respects_max_chars(self):
        chunk = ["Alice: " + "word " * 100]
        result = get_smart_overlap(chunk, 50)
        assert len(result) <= 100  # some flexibility for boundary alignment


class TestGetLastSentence:

    def test_returns_last_sentence(self):
        text = "First sentence here. Second sentence here. Third sentence here."
        result = get_last_sentence(text, 100)
        assert "Third sentence here" in result

    def test_respects_max_chars(self):
        text = "Short. " * 20
        result = get_last_sentence(text, 30)
        assert len(result) <= 60  # some flexibility

    def test_empty_text(self):
        result = get_last_sentence("", 100)
        assert isinstance(result, str)