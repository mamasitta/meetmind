from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.schemas.agent import AgentReportResponse, AgentReport
from app.services.meeting_db_service import get_meeting_with_all_data
from app.agents.meeting_agent import run_meeting_agent


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/meetings/{meeting_id}/analyse", response_model=AgentReportResponse)
async def analyse_meeting(meeting_id: UUID, db: AsyncSession = Depends(get_db)):
    # first check the meeting exists
    meeting = await get_meeting_with_all_data(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # run the full agent loop — this makes multiple Claude API calls
    report_data = await run_meeting_agent(
        transcript = meeting.transcript,
        db = db
    )

    return AgentReportResponse(
        meeting_id = meeting_id,
        report = AgentReport(**report_data)
    )