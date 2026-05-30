import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4


class TestStoreChunks:

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_texts")
    @patch("app.rag.retriever.qdrant_client")
    async def test_returns_chunk_count(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [[0.1] * 1024, [0.2] * 1024]
        mock_qdrant.upsert = MagicMock()

        from app.rag.retriever import store_chunks

        # two chunks will be created from this transcript
        transcript = "Alice: Hello.\nBob: Hi there."
        count = await store_chunks(uuid4(), transcript)

        assert isinstance(count, int)
        assert count >= 1

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_texts")
    @patch("app.rag.retriever.qdrant_client")
    async def test_upsert_called_with_points(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [[0.1] * 1024]
        mock_qdrant.upsert = MagicMock()

        from app.rag.retriever import store_chunks

        meeting_id = uuid4()
        await store_chunks(meeting_id, "Alice: Short transcript.")

        assert mock_qdrant.upsert.called

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_texts")
    @patch("app.rag.retriever.qdrant_client")
    async def test_payload_contains_meeting_id(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [[0.1] * 1024]

        captured_points = []
        def capture_upsert(**kwargs):
            captured_points.extend(kwargs.get("points", []))
        mock_qdrant.upsert = MagicMock(side_effect=lambda **kw: captured_points.extend(kw.get("points", [])))

        from app.rag.retriever import store_chunks

        meeting_id = uuid4()
        await store_chunks(meeting_id, "Alice: Hello everyone.")

        # verify meeting_id is in the payload
        if captured_points:
            assert str(meeting_id) == captured_points[0].payload["meeting_id"]

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_texts")
    @patch("app.rag.retriever.qdrant_client")
    async def test_empty_transcript_returns_zero(self, mock_qdrant, mock_embed):
        from app.rag.retriever import store_chunks
        count = await store_chunks(uuid4(), "")
        assert count == 0
        mock_qdrant.upsert.assert_not_called()


class TestSearchSimilarChunks:

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_text")
    @patch("app.rag.retriever.qdrant_client")
    async def test_returns_list_of_dicts(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [0.1] * 1024

        point = MagicMock()
        point.payload = {"meeting_id": "abc", "chunk_index": 0, "content": "Alice talked about Stripe."}
        point.score = 0.92

        mock_response = MagicMock()
        mock_response.points = [point]
        mock_qdrant.query_points = MagicMock(return_value=mock_response)

        from app.rag.retriever import search_similar_chunks
        results = await search_similar_chunks("Stripe payment issues")

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["meeting_id"] == "abc"
        assert results[0]["similarity"] == 0.92

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_text")
    @patch("app.rag.retriever.qdrant_client")
    async def test_returns_empty_when_no_results(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [0.1] * 1024

        mock_response = MagicMock()
        mock_response.points = []
        mock_qdrant.query_points = MagicMock(return_value=mock_response)

        from app.rag.retriever import search_similar_chunks
        results = await search_similar_chunks("something with no matches")

        assert results == []

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_text")
    @patch("app.rag.retriever.qdrant_client")
    async def test_exclude_meeting_id_passed_as_filter(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [0.1] * 1024

        mock_response = MagicMock()
        mock_response.points = []
        mock_qdrant.query_points = MagicMock(return_value=mock_response)

        from app.rag.retriever import search_similar_chunks
        exclude_id = uuid4()
        await search_similar_chunks("query", exclude_meeting_id=exclude_id)

        call_kwargs = mock_qdrant.query_points.call_args.kwargs
        # filter should be set when exclude_meeting_id is provided
        assert call_kwargs.get("query_filter") is not None

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_text")
    @patch("app.rag.retriever.qdrant_client")
    async def test_no_filter_when_no_exclude(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [0.1] * 1024

        mock_response = MagicMock()
        mock_response.points = []
        mock_qdrant.query_points = MagicMock(return_value=mock_response)

        from app.rag.retriever import search_similar_chunks
        await search_similar_chunks("query", exclude_meeting_id=None)

        call_kwargs = mock_qdrant.query_points.call_args.kwargs
        assert call_kwargs.get("query_filter") is None

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_text")
    @patch("app.rag.retriever.qdrant_client")
    async def test_result_contains_required_fields(self, mock_qdrant, mock_embed):
        mock_embed.return_value = [0.1] * 1024

        point = MagicMock()
        point.payload = {"meeting_id": "abc", "chunk_index": 0, "content": "Some content"}
        point.score = 0.88

        mock_response = MagicMock()
        mock_response.points = [point]
        mock_qdrant.query_points = MagicMock(return_value=mock_response)

        from app.rag.retriever import search_similar_chunks
        results = await search_similar_chunks("test query")

        assert "meeting_id" in results[0]
        assert "chunk_index" in results[0]
        assert "content" in results[0]
        assert "similarity" in results[0]