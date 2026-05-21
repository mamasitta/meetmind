# tests/test_extraction.py
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import ValidationError
from app.services.extraction import extract_from_transcript
from app.prompts.extraction_prompts import ExtractionPrompts
from app.schemas.meeting import (
    MeetingExtraction, ActionItem, Decision, Risk,
    TranscriptRequest
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def make_mock_response(data: dict) -> MagicMock:
    """Builds a fake AsyncAnthropic response matching response.content[0].text"""
    mock_content = MagicMock()
    mock_content.text = json.dumps(data)
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


def valid_extraction_payload(**overrides) -> dict:
    """
    Minimal valid payload matching MeetingExtraction schema.
    Override specific fields per test to keep tests focused.
    """
    base = {
        "summary": "Team aligned on tasks and identified key risks.",
        "action_items": [],
        "decisions": [],
        "general_risks": [],
        "participants": ["Alice", "Bob"]
    }
    base.update(overrides)
    return base


# ── Schema unit tests (no API calls, pure Pydantic) ───────────────────────────

class TestTranscriptRequestSchema:
    """
    Tests for the request schema validation.
    These run instantly — no mocking needed, pure Pydantic logic.
    """

    def test_valid_request_accepted(self):
        req = TranscriptRequest(title="Sprint sync", transcript="Alice: I'll fix the bug.")
        assert req.title == "Sprint sync"

    def test_empty_transcript_raises(self):
        # CHANGE tested: field_validator("transcript") rejects empty string
        with pytest.raises(ValidationError, match="empty"):
            TranscriptRequest(title="Test", transcript="")

    def test_whitespace_only_transcript_raises(self):
        # CHANGE tested: field_validator("transcript") rejects whitespace-only
        with pytest.raises(ValidationError, match="empty"):
            TranscriptRequest(title="Test", transcript="     ")

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            TranscriptRequest(transcript="Alice: I'll fix the bug.")

    def test_missing_transcript_raises(self):
        with pytest.raises(ValidationError):
            TranscriptRequest(title="Test")


class TestRiskSchema:

    def test_valid_severity_low(self):
        risk = Risk(description="Minor delay", severity="low")
        assert risk.severity == "low"

    def test_valid_severity_medium(self):
        risk = Risk(description="Some concern", severity="medium")
        assert risk.severity == "medium"

    def test_valid_severity_high(self):
        risk = Risk(description="Critical blocker", severity="high")
        assert risk.severity == "high"

    def test_default_severity_is_medium(self):
        risk = Risk(description="Unknown concern")
        assert risk.severity == "medium"

    def test_invalid_severity_raises(self):
        # CHANGE tested: severity: SeverityLevel rejects values outside enum
        with pytest.raises(ValidationError):
            Risk(description="Some risk", severity="critical")

    def test_invalid_severity_uppercase_raises(self):
        # CHANGE tested: "HIGH" is not "high" — Literal is case sensitive
        with pytest.raises(ValidationError):
            Risk(description="Some risk", severity="HIGH")

    def test_invalid_severity_urgent_raises(self):
        # Claude sometimes returns "urgent" — this must be caught
        with pytest.raises(ValidationError):
            Risk(description="Some risk", severity="urgent")

    def test_related_to_optional(self):
        risk = Risk(description="General concern")
        assert risk.related_to is None

    def test_related_to_accepted(self):
        risk = Risk(description="Concern", related_to="action: Deploy API")
        assert risk.related_to == "action: Deploy API"


class TestActionItemSchema:

    def test_valid_priority_values(self):
        for priority in ["low", "medium", "high"]:
            item = ActionItem(description="Do something", priority=priority)
            assert item.priority == priority

    def test_default_priority_is_medium(self):
        item = ActionItem(description="Do something")
        assert item.priority == "medium"

    def test_invalid_priority_raises(self):
        # CHANGE tested: priority: PriorityLevel rejects "critical", "urgent" etc.
        with pytest.raises(ValidationError):
            ActionItem(description="Do something", priority="critical")

    def test_invalid_priority_uppercase_raises(self):
        with pytest.raises(ValidationError):
            ActionItem(description="Do something", priority="HIGH")

    def test_invalid_priority_urgent_raises(self):
        # Claude sometimes returns "urgent" for high-priority items
        with pytest.raises(ValidationError):
            ActionItem(description="Do something", priority="urgent")

    def test_owner_optional(self):
        item = ActionItem(description="Fix the bug")
        assert item.owner is None

    def test_due_date_optional(self):
        item = ActionItem(description="Fix the bug")
        assert item.due_date is None

    def test_risks_default_empty_list(self):
        item = ActionItem(description="Fix the bug")
        assert item.risks == []

    def test_nested_risk_accepted(self):
        item = ActionItem(
            description="Deploy API",
            risks=[Risk(description="Migration risk", severity="high")]
        )
        assert len(item.risks) == 1
        assert item.risks[0].severity == "high"

    def test_nested_risk_with_invalid_severity_raises(self):
        # Validation propagates through nested models
        with pytest.raises(ValidationError):
            ActionItem(
                description="Deploy API",
                risks=[Risk(description="Risk", severity="critical")]
            )


class TestMeetingExtractionSchema:

    def test_empty_summary_raises(self):
        # CHANGE tested: field_validator("summary") rejects empty string
        with pytest.raises(ValidationError, match="empty"):
            MeetingExtraction(
                summary="",
                action_items=[],
                decisions=[],
                general_risks=[],
                participants=[]
            )

    def test_whitespace_summary_raises(self):
        # CHANGE tested: whitespace-only summary also rejected
        with pytest.raises(ValidationError, match="empty"):
            MeetingExtraction(
                summary="   ",
                action_items=[],
                decisions=[],
                general_risks=[],
                participants=[]
            )

    def test_valid_extraction_accepted(self):
        extraction = MeetingExtraction(
            summary="Team met and agreed on priorities.",
            action_items=[],
            decisions=[],
            general_risks=[],
            participants=["Alice"]
        )
        assert extraction.summary == "Team met and agreed on priorities."

    def test_all_lists_default_empty(self):
        extraction = MeetingExtraction(summary="Short meeting.")
        assert extraction.action_items == []
        assert extraction.decisions == []
        assert extraction.general_risks == []
        assert extraction.participants == []


# ── Prompt builder tests ──────────────────────────────────────────────────────

class TestExtractionPrompt:

    def test_transcript_injected_into_prompt(self, sample_transcript):
        prompt = ExtractionPrompts.build_extraction_prompt(sample_transcript)
        assert sample_transcript in prompt

    def test_prompt_requires_json_only_output(self, sample_transcript):
        prompt = ExtractionPrompts.build_extraction_prompt(sample_transcript)
        assert "ONLY valid JSON" in prompt

    def test_all_schema_fields_present_in_prompt(self, sample_transcript):
        prompt = ExtractionPrompts.build_extraction_prompt(sample_transcript)
        for field in ["summary", "action_items", "decisions", "general_risks", "participants"]:
            assert field in prompt, f"Field '{field}' missing from prompt"

    def test_enum_values_documented_in_prompt(self, sample_transcript):
        prompt = ExtractionPrompts.build_extraction_prompt(sample_transcript)
        for value in ["low", "medium", "high"]:
            assert value in prompt

    def test_different_transcripts_produce_different_prompts(self):
        prompt_a = ExtractionPrompts.build_extraction_prompt("Alice: I'll fix the bug.")
        prompt_b = ExtractionPrompts.build_extraction_prompt("Bob: Deploy by Friday.")
        assert prompt_a != prompt_b


# ── Extraction service tests ──────────────────────────────────────────────────

class TestExtractFromTranscript:
    """
    Tests for the async extract_from_transcript function.
    Claude client is always mocked — no real API calls, no cost.
    """

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_returns_meeting_extraction_type(
        self, mock_client, sample_transcript
    ):
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(valid_extraction_payload())
        )
        result = await extract_from_transcript(sample_transcript)
        assert isinstance(result, MeetingExtraction)

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_claude_called_exactly_once(
        self, mock_client, sample_transcript
    ):
        # Verifies we don't accidentally call Claude multiple times per request
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(valid_extraction_payload())
        )
        await extract_from_transcript(sample_transcript)
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_correct_model_from_config(
        self, mock_client, sample_transcript
    ):
        from app.core.config import settings
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(valid_extraction_payload())
        )
        await extract_from_transcript(sample_transcript)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == settings.claude_model

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_action_item_all_fields_parsed(
        self, mock_client, sample_transcript
    ):
        payload = valid_extraction_payload(
            action_items=[{
                "description": "Deploy the API",
                "owner": "Bob",
                "due_date": "Friday",
                "priority": "high",
                "risks": []
            }]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )
        result = await extract_from_transcript(sample_transcript)

        item = result.action_items[0]
        assert item.description == "Deploy the API"
        assert item.owner == "Bob"
        assert item.due_date == "Friday"
        assert item.priority == "high"
        assert item.risks == []

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_multiple_action_items_all_parsed(
        self, mock_client, sample_transcript
    ):
        # Tests the loop — not just first item
        payload = valid_extraction_payload(
            action_items=[
                {"description": "Task one", "owner": "Alice", "due_date": None, "priority": "high", "risks": []},
                {"description": "Task two", "owner": "Bob", "due_date": "Monday", "priority": "medium", "risks": []},
                {"description": "Task three", "owner": None, "due_date": None, "priority": "low", "risks": []},
            ]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )
        result = await extract_from_transcript(sample_transcript)

        assert len(result.action_items) == 3
        assert result.action_items[0].owner == "Alice"
        assert result.action_items[1].due_date == "Monday"
        assert result.action_items[2].priority == "low"

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_nested_risk_in_action_item(
        self, mock_client, sample_transcript
    ):
        payload = valid_extraction_payload(
            action_items=[{
                "description": "Deploy the API",
                "owner": "Bob",
                "due_date": "Friday",
                "priority": "high",
                "risks": [{
                    "description": "Database migration could break production",
                    "related_to": "action: Deploy the API",
                    "severity": "high"
                }]
            }]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )
        result = await extract_from_transcript(sample_transcript)

        risk = result.action_items[0].risks[0]
        assert risk.description == "Database migration could break production"
        assert risk.severity == "high"
        assert risk.related_to.startswith("action:")

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_nested_risk_in_decision(
        self, mock_client, sample_transcript
    ):
        payload = valid_extraction_payload(
            decisions=[{
                "description": "Use PostgreSQL",
                "made_by": "Alice",
                "risks": [{
                    "description": "Migration complexity is high",
                    "related_to": "decision: Use PostgreSQL",
                    "severity": "medium"
                }]
            }]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )
        result = await extract_from_transcript(sample_transcript)

        decision = result.decisions[0]
        assert decision.made_by == "Alice"
        assert decision.risks[0].severity == "medium"
        assert decision.risks[0].related_to.startswith("decision:")

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_general_risks_parsed_at_top_level(
        self, mock_client, sample_transcript
    ):
        payload = valid_extraction_payload(
            general_risks=[{
                "description": "Team is understaffed",
                "related_to": "general",
                "severity": "medium"
            }]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )
        result = await extract_from_transcript(sample_transcript)

        assert len(result.general_risks) == 1
        assert result.general_risks[0].related_to == "general"

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_null_optional_fields_accepted(
        self, mock_client, sample_transcript
    ):
        payload = valid_extraction_payload(
            action_items=[{
                "description": "Fix the bug",
                "owner": None,
                "due_date": None,
                "priority": "medium",
                "risks": [{
                    "description": "Unknown impact",
                    "related_to": None,
                    "severity": "low"
                }]
            }]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )
        result = await extract_from_transcript(sample_transcript)

        item = result.action_items[0]
        assert item.owner is None
        assert item.due_date is None
        assert item.risks[0].related_to is None

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_empty_lists_all_valid(
        self, mock_client, sample_transcript
    ):
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(valid_extraction_payload())
        )
        result = await extract_from_transcript(sample_transcript)

        assert result.action_items == []
        assert result.decisions == []
        assert result.general_risks == []

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_participants_all_returned(
        self, mock_client, sample_transcript
    ):
        payload = valid_extraction_payload(
            participants=["Alice", "Bob", "Carol"]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )
        result = await extract_from_transcript(sample_transcript)

        assert set(result.participants) == {"Alice", "Bob", "Carol"}

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_raises_on_plain_text_response(
        self, mock_client, sample_transcript
    ):
        """Claude occasionally ignores JSON instruction — must raise clearly."""
        mock_content = MagicMock()
        mock_content.text = "Sorry, I cannot process this transcript."
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="invalid JSON"):
            await extract_from_transcript(sample_transcript)

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_raises_on_markdown_wrapped_json(
        self, mock_client, sample_transcript
    ):
        """
        Claude sometimes wraps JSON in ```json``` fences despite instructions.
        This should raise ValueError, not crash with a confusing AttributeError.
        If this test fails it means you need to strip markdown fences in extraction.py.
        """
        mock_content = MagicMock()
        mock_content.text = "```json\n{\"summary\": \"test\"}\n```"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="invalid JSON"):
            await extract_from_transcript(sample_transcript)

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_invalid_priority_from_claude_raises(
        self, mock_client, sample_transcript
    ):
        """
        CHANGE tested: if Claude returns priority='critical' it now raises
        ValidationError because PriorityLevel = Literal['low','medium','high'].
        Before this change it would silently save 'critical' to the database.
        """
        payload = valid_extraction_payload(
            action_items=[{
                "description": "Fix bug",
                "owner": None,
                "due_date": None,
                "priority": "critical",  # invalid — Claude sometimes does this
                "risks": []
            }]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )

        with pytest.raises((ValueError, ValidationError)):
            await extract_from_transcript(sample_transcript)

    @pytest.mark.asyncio
    @patch("app.services.extraction.client")
    async def test_invalid_severity_from_claude_raises(
        self, mock_client, sample_transcript
    ):
        """
        CHANGE tested: if Claude returns severity='urgent' it now raises.
        Before this change it would silently save 'urgent' to the database.
        """
        payload = valid_extraction_payload(
            general_risks=[{
                "description": "Some risk",
                "related_to": "general",
                "severity": "urgent"  # invalid — Claude sometimes does this
            }]
        )
        mock_client.messages.create = AsyncMock(
            return_value=make_mock_response(payload)
        )

        with pytest.raises((ValueError, ValidationError)):
            await extract_from_transcript(sample_transcript)