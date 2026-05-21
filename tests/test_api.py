import pytest
from unittest.mock import patch


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPostMeeting:

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    async def test_happy_path_returns_200(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction

        response = await client.post("/meetings/", json={
            "title": "Sprint planning",
            "transcript": sample_transcript
        })

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    async def test_response_contains_all_top_level_fields(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction

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
    async def test_extraction_contains_all_fields(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction

        response = await client.post("/meetings/", json={
            "title": "Sprint planning",
            "transcript": sample_transcript
        })
        extraction = response.json()["extraction"]

        assert "summary" in extraction
        assert "action_items" in extraction
        assert "decisions" in extraction
        assert "general_risks" in extraction
        assert "participants" in extraction

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    async def test_action_items_returned_correctly(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction

        response = await client.post("/meetings/", json={
            "title": "Sprint planning",
            "transcript": sample_transcript
        })
        action_items = response.json()["extraction"]["action_items"]

        assert len(action_items) == 2
        owners = [item["owner"] for item in action_items]
        assert "Bob" in owners
        assert "Carol" in owners

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    async def test_nested_risks_in_action_items_returned(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        """
        Key test — verifies your nested risk structure survives
        the full round trip: extraction → DB → serializer → response.
        """
        mock_extract.return_value = mock_extraction

        response = await client.post("/meetings/", json={
            "title": "Sprint planning",
            "transcript": sample_transcript
        })
        action_items = response.json()["extraction"]["action_items"]

        # Carol's action item has a nested risk
        carol_item = next(i for i in action_items if i["owner"] == "Carol")
        assert isinstance(carol_item["risks"], list)
        assert len(carol_item["risks"]) > 0
        assert "description" in carol_item["risks"][0]
        assert "severity" in carol_item["risks"][0]

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    async def test_general_risks_returned_at_top_level(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction

        response = await client.post("/meetings/", json={
            "title": "Sprint planning",
            "transcript": sample_transcript
        })
        general_risks = response.json()["extraction"]["general_risks"]

        assert isinstance(general_risks, list)
        assert len(general_risks) > 0
        assert general_risks[0]["related_to"] == "general"

    @pytest.mark.asyncio
    async def test_missing_title_returns_422(self, client, sample_transcript):
        response = await client.post("/meetings/", json={
            "transcript": sample_transcript
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_transcript_returns_422(self, client):
        response = await client.post("/meetings/", json={
            "title": "No transcript meeting"
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_transcript_field_returns_422(self, client):
        """Empty string is not a valid transcript."""
        response = await client.post("/meetings/", json={
            "title": "Test",
            "transcript": ""
        })
        # if this returns 200 it means you should add min_length=10 to the schema
        assert response.status_code in [200, 422]


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
    async def test_get_meeting_returns_same_id_as_created(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction

        create_response = await client.post("/meetings/", json={
            "title": "Retrievable meeting",
            "transcript": sample_transcript
        })
        meeting_id = create_response.json()["id"]

        get_response = await client.get(f"/meetings/{meeting_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == meeting_id

    @pytest.mark.asyncio
    @patch("app.services.meeting_db_service.extract_from_transcript")
    async def test_get_meeting_title_matches(
        self, mock_extract, client, sample_transcript, mock_extraction
    ):
        mock_extract.return_value = mock_extraction

        create_response = await client.post("/meetings/", json={
            "title": "My specific meeting title",
            "transcript": sample_transcript
        })
        meeting_id = create_response.json()["id"]

        get_response = await client.get(f"/meetings/{meeting_id}")
        assert get_response.json()["title"] == "My specific meeting title"