import pytest
from unittest.mock import MagicMock, patch


class TestEmbedText:

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_returns_list_of_floats(self, mock_vo):
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_vo.embed.return_value = mock_result

        from app.rag.embiddings import embed_text
        result = await embed_text("Alice said the deadline is Friday")

        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_uses_document_input_type(self, mock_vo):
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_vo.embed.return_value = mock_result

        from app.rag.embiddings import embed_text
        await embed_text("some text")

        call_kwargs = mock_vo.embed.call_args.kwargs
        assert call_kwargs["input_type"] == "document"

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_uses_correct_model(self, mock_vo):
        from app.core.config import settings
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_vo.embed.return_value = mock_result

        from app.rag.embiddings import embed_text
        await embed_text("test")

        call_kwargs = mock_vo.embed.call_args.kwargs
        assert call_kwargs["model"] == settings.embedding_model


class TestEmbedTexts:

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_returns_list_of_lists(self, mock_vo):
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024, [0.2] * 1024]
        mock_vo.embed.return_value = mock_result

        from app.rag.embiddings import embed_texts
        result = await embed_texts(["text one", "text two"])

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], list)

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_empty_list_returns_empty(self, mock_vo):
        from app.rag.embiddings import embed_texts
        result = await embed_texts([])
        assert result == []
        mock_vo.embed.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_single_api_call_for_multiple_texts(self, mock_vo):
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024] * 3
        mock_vo.embed.return_value = mock_result

        from app.rag.embiddings import embed_texts
        await embed_texts(["a", "b", "c"])

        # should be exactly one API call — not one per text
        assert mock_vo.embed.call_count == 1


class TestEmbedQuery:

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_uses_query_input_type(self, mock_vo):
        # critical — query embeddings use different input_type than documents
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_vo.embed.return_value = mock_result

        from app.rag.embiddings import embed_query
        await embed_query("what did Alice say about budget?")

        call_kwargs = mock_vo.embed.call_args.kwargs
        assert call_kwargs["input_type"] == "query"

    @pytest.mark.asyncio
    @patch("app.rag.embiddings.vo")
    async def test_query_differs_from_document_type(self, mock_vo):
        # embed_text uses "document", embed_query uses "query"
        # mixing these breaks retrieval quality — test they are different
        mock_result = MagicMock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_vo.embed.return_value = mock_result

        from app.rag.embiddings import embed_text, embed_query

        await embed_text("document text")
        doc_type = mock_vo.embed.call_args.kwargs["input_type"]

        await embed_query("search query")
        query_type = mock_vo.embed.call_args.kwargs["input_type"]

        assert doc_type == "document"
        assert query_type == "query"
        assert doc_type != query_type