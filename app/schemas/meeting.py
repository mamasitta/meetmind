from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class TranscriptRequest(BaseModel):
    title: str = Field(description="Meeting title")
    transcript: str = Field(description="Full meeting transcript text")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Product sync 12 May",
                "transcript": "Alice: We need to finish login page by Friday. Ban: logs have bug with email sending"
            }
        }


# Claude extrackts
class Risk(BaseModel):
    description: str = Field(description="Potential problem or blocker identified")
    related_to: Optional[str] = Field(None, description="What this risk related to: 'decision: <description>' or 'action: <description>' or 'general'")
    severity: str = Field(default="medium", description="low, medium or high")


class ActionItem(BaseModel):
    description: str = Field(description="What needs to be done")
    owner: Optional[str] = Field(None, description="Person responsible, if mentioned")
    due_date: Optional[str] = Field(None, description="deadline if mentioned, e.g. 'Friday' or '2026-05-13'")
    priority: str = Field(default="medium", description="low, medium or high")
    risks: list[Risk] = Field(default_factory=list, description="Risks specifically related with this action item")


class Decision(BaseModel):
    description: str = Field(description="What was decided")
    made_by: Optional[str] = Field(None, description="Who made the decision, if clear")
    risks: list[Risk] = Field(default_factory=list, description="Risks specifically related with this decision")


class MeetingExtraction(BaseModel):
    summary: str = Field(description="2-3 short sentence summary of meeting")
    action_items: list[ActionItem] = Field(default_factory=list)
    decigions: list[Decision] = Field(default_factory=list)
    general_risks: list[Risk] = Field(default_factory=list, description="Risks that affect all project/meeting")
    participants: list[str] = Field(default_factory=list, description="Names of people who spoke or attand the meeting")


# What we send back too user
class MeetingResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    extraction: MeetingExtraction

    class Config:
        from_attributes = True