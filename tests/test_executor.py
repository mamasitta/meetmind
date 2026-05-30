import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestRunExtractMeetingData:

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.extract_from_transcript")
    async def test_returns_dict(self, mock_extract, mock_extraction):
        mock_extract.return_value = mock_extraction

        from app.agents.tools.executor import run_extract_meeting_data
        result = await run_extract_meeting_data("Alice: Hello")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.extract_from_transcript")
    async def test_contains_summary(self, mock_extract, mock_extraction):
        mock_extract.return_value = mock_extraction

        from app.agents.tools.executor import run_extract_meeting_data
        result = await run_extract_meeting_data("Alice: Hello")

        assert "summary" in result

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.extract_from_transcript")
    async def test_passes_transcript_to_extraction(self, mock_extract, mock_extraction):
        mock_extract.return_value = mock_extraction

        from app.agents.tools.executor import run_extract_meeting_data
        await run_extract_meeting_data("Alice: specific transcript text")

        mock_extract.assert_called_once_with("Alice: specific transcript text")


class TestRunSearchPastMeetings:

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.search_similar_chunks")
    async def test_returns_found_zero_when_no_results(self, mock_search):
        mock_search.return_value = []

        from app.agents.tools.executor import run_search_past_meetings
        result = await run_search_past_meetings("Stripe", limit=3)

        assert result["found"] == 0
        assert result["meetings"] == []

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.search_similar_chunks")
    async def test_groups_chunks_by_meeting(self, mock_search):
        # two chunks from same meeting should be grouped
        mock_search.return_value = [
            {"meeting_id": "abc", "chunk_index": 0, "content": "Stripe sandbox down.", "similarity": 0.95},
            {"meeting_id": "abc", "chunk_index": 1, "content": "Blocking the release.", "similarity": 0.90},
        ]

        from app.agents.tools.executor import run_search_past_meetings
        result = await run_search_past_meetings("Stripe", limit=3)

        # two chunks from same meeting = one meeting in results
        assert result["found"] == 1
        assert len(result["meetings"][0]["excerpts"]) == 2

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.search_similar_chunks")
    async def test_multiple_meetings_returned(self, mock_search):
        mock_search.return_value = [
            {"meeting_id": "abc", "chunk_index": 0, "content": "Meeting A content.", "similarity": 0.95},
            {"meeting_id": "xyz", "chunk_index": 0, "content": "Meeting B content.", "similarity": 0.88},
        ]

        from app.agents.tools.executor import run_search_past_meetings
        result = await run_search_past_meetings("payments", limit=3)

        assert result["found"] == 2

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.search_similar_chunks")
    async def test_exclude_meeting_id_passed_through(self, mock_search):
        mock_search.return_value = []
        exclude_id = uuid4()

        from app.agents.tools.executor import run_search_past_meetings
        await run_search_past_meetings("query", limit=3, exclude_meeting_id=exclude_id)

        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["exclude_meeting_id"] == exclude_id


class TestRunAssessOverallRisk:

    def test_no_risks_returns_low(self):
        from app.agents.tools.executor import run_assess_overall_risk
        result = run_assess_overall_risk([], [], [])
        assert result["overall_risk_level"] == "low"
        assert result["total_risks"] == 0

    def test_one_risk_returns_medium(self):
        from app.agents.tools.executor import run_assess_overall_risk
        result = run_assess_overall_risk(["API is down"], [], [])
        assert result["overall_risk_level"] == "medium"

    def test_three_risks_returns_high(self):
        from app.agents.tools.executor import run_assess_overall_risk
        result = run_assess_overall_risk(["risk1", "risk2"], ["risk3"], [])
        assert result["overall_risk_level"] == "high"

    def test_six_risks_returns_critical(self):
        from app.agents.tools.executor import run_assess_overall_risk
        result = run_assess_overall_risk(
            ["r1", "r2", "r3"],
            ["r4", "r5"],
            ["r6"]
        )
        assert result["overall_risk_level"] == "critical"

    def test_breakdown_counts_correct(self):
        from app.agents.tools.executor import run_assess_overall_risk
        result = run_assess_overall_risk(["a", "b"], ["c"], ["d", "e"])
        assert result["breakdown"]["from_action_items"] == 2
        assert result["breakdown"]["from_decisions"] == 1
        assert result["breakdown"]["general"] == 2
        assert result["total_risks"] == 5

    def test_returns_reasoning_string(self):
        from app.agents.tools.executor import run_assess_overall_risk
        result = run_assess_overall_risk(["risk"], [], [])
        assert isinstance(result["reasoning"], str)
        assert len(result["reasoning"]) > 0


class TestExecuteTool:

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.extract_from_transcript")
    async def test_extract_tool_returns_json_string(self, mock_extract, mock_extraction):
        mock_extract.return_value = mock_extraction

        from app.agents.tools.executor import execute_tool
        result = await execute_tool(
            tool_name  = "extract_meeting_data",
            tool_input = {"transcript": "Alice: Hello"},
            db         = MagicMock()
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    @patch("app.agents.tools.executor.search_similar_chunks")
    async def test_search_tool_returns_json_string(self, mock_search):
        mock_search.return_value = []

        from app.agents.tools.executor import execute_tool
        result = await execute_tool(
            tool_name  = "search_past_meetings",
            tool_input = {"query": "Stripe", "limit": 3},
            db         = MagicMock()
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "found" in parsed

    @pytest.mark.asyncio
    async def test_risk_tool_returns_json_string(self):
        from app.agents.tools.executor import execute_tool
        result = await execute_tool(
            tool_name  = "assess_overall_risk",
            tool_input = {"action_item_risks": ["risk"], "decision_risks": [], "general_risks": []},
            db         = MagicMock()
        )

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "overall_risk_level" in parsed

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error_json(self):
        from app.agents.tools.executor import execute_tool
        result = await execute_tool(
            tool_name  = "nonexistent_tool",
            tool_input = {},
            db         = MagicMock()
        )

        parsed = json.loads(result)
        assert "error" in parsed