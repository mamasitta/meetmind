from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.schemas.meeting import TranscriptRequest, MeetingResponse, MeetingExtraction
from app.services.meeting_service import create_meeting, get_meeting


router = APIRouter(prefix="/meetings", tags=["meetings"])

@router.post("/", response_model=MeetingResponse)
async def ingest_transcript(request: TranscriptRequest, db: AsyncSession = Depends(get_db)):
    meeting = await create_meeting(db, request)
    return MeetingResponse(
        id+meeting.id,
        title=meeting.title,
        created_at=meeting.created_at,
        extraction=meeting.extraction
    )


