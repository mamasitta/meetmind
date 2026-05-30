import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPostMeeting:

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    async def test_happy_path_returns_200(
        self, mock_store, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 2

        response = await client.post("/meetings/", json={
            "title": "Sprint planning",
            "transcript": sample_transcript
        })

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    async def test_response_has_required_fields(
        self, mock_store, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 2

        response = await client.post("/meetings/", json={
            "title": "Sprint planning",
            "transcript": sample_transcript
        })
        data = response.json()

        assert "id" in data
        assert "title" in data
        assert "created_at" in data
        assert "extraction" in data

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    async def test_extraction_fields_present(
        self, mock_store, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 2

        response = await client.post("/meetings/", json={
            "title": "Test",
            "transcript": sample_transcript
        })
        extraction = response.json()["extraction"]

        assert "summary" in extraction
        assert "action_items" in extraction
        assert "decisions" in extraction
        assert "general_risks" in extraction
        assert "participants" in extraction

    @pytest.mark.asyncio
    async def test_missing_title_returns_422(self, client, sample_transcript):
        response = await client.post("/meetings/", json={
            "transcript": sample_transcript
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_transcript_returns_422(self, client):
        response = await client.post("/meetings/", json={
            "title": "Test meeting"
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_422(self, client):
        response = await client.post("/meetings/", json={
            "title": "Test",
            "transcript": ""
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    async def test_store_chunks_called_on_create(
        self, mock_store, mock_extract, client, sample_transcript, mock_extraction
    ):
        # verify RAG chunking runs every time a meeting is created
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 3

        await client.post("/meetings/", json={
            "title": "Test",
            "transcript": sample_transcript
        })

        assert mock_store.called


class TestGetMeeting:

    @pytest.mark.asyncio
    async def test_nonexistent_meeting_returns_404(self, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/meetings/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client):
        response = await client.get("/meetings/not-a-uuid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    async def test_get_returns_same_id(
        self, mock_store, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 2

        create = await client.post("/meetings/", json={
            "title": "Retrievable meeting",
            "transcript": sample_transcript
        })
        meeting_id = create.json()["id"]

        get = await client.get(f"/meetings/{meeting_id}")
        assert get.status_code == 200
        assert get.json()["id"] == meeting_id

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    async def test_get_returns_correct_title(
        self, mock_store, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 2

        create = await client.post("/meetings/", json={
            "title": "My unique title",
            "transcript": sample_transcript
        })
        meeting_id = create.json()["id"]

        get = await client.get(f"/meetings/{meeting_id}")
        assert get.json()["title"] == "My unique title"


class TestAgentEndpoint:

    @pytest.mark.asyncio
    async def test_nonexistent_meeting_returns_404(self, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post(f"/agent/meetings/{fake_id}/analyse")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client):
        response = await client.post("/agent/meetings/not-a-uuid/analyse")
        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    @patch("app.api.agent_api_route.run_meeting_agent")
    async def test_analyse_returns_report(
        self, mock_agent, mock_store, mock_extract,
        client, sample_transcript, mock_extraction, mock_agent_report
    ):
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 2
        mock_agent.return_value = mock_agent_report

        # create a meeting first
        create = await client.post("/meetings/", json={
            "title": "Meeting to analyse",
            "transcript": sample_transcript
        })
        meeting_id = create.json()["id"]

        # run the agent
        response = await client.post(f"/agent/meetings/{meeting_id}/analyse")

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    @patch("app.services.meeting_db_service.store_chunks")
    @patch("app.api.agent_api_route.run_meeting_agent")
    async def test_analyse_response_has_all_fields(
        self, mock_agent, mock_store, mock_extract,
        client, sample_transcript, mock_extraction, mock_agent_report
    ):
        mock_extract.return_value = mock_extraction
        mock_store.return_value = 2
        mock_agent.return_value = mock_agent_report

        create = await client.post("/meetings/", json={
            "title": "Meeting to analyse",
            "transcript": sample_transcript
        })
        meeting_id = create.json()["id"]

        response = await client.post(f"/agent/meetings/{meeting_id}/analyse")
        data = response.json()

        assert "meeting_id" in data
        assert "report" in data

        report = data["report"]
        assert "executive_summary" in report
        assert "key_findings" in report
        assert "historical_context" in report
        assert "overall_risk_level" in report
        assert "recommended_actions" in report
        assert "follow_up_required" in report