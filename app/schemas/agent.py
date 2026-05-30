from pydantic import BaseModel
from uuid import UUID


class AgentReport(BaseModel):
    executive_summary: str
    key_findings: list[str]
    historical_context: str
    overall_risk_level: str
    recommended_actions: list[str]
    follow_up_required: bool


class AgentReportResponse(BaseModel):
    meeting_id: UUID
    report: AgentReport