from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.schemas.meeting import TranscriptRequest, MeetingResponse
from app.services.meeting_db_service import create_meeting, get_meeting_with_all_data
from app.serializers.meeting_to_response_serializer import meeting_to_response


router = APIRouter(prefix="/meetings", tags=["meetings"])

@router.post("/", response_model=MeetingResponse)
async def ingest_transcript(request: TranscriptRequest, db: AsyncSession = Depends(get_db)):
    print("Hi")
    meeting, meeting_extraction = await create_meeting(db, request)
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        created_at=meeting.created_at,
        extraction=meeting_extraction   
        )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_by_id(meeting_id: UUID, db: AsyncSession = Depends(get_db)):
    meeting = await get_meeting_with_all_data(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting_to_response(meeting)
