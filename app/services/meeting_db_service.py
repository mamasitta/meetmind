from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.models.meeting import Meeting, ActionItem as ActionItemModel
from app.schemas.meeting import TranscriptRequest, MeetingExtraction
from app.services.extraction import extract_from_transcript


async def create_meeting(db: AsyncSession, request: TranscriptRequest) -> Meeting:
    extraction = extract_from_transcript(request.transcript)
    
    # Create meeting
    meeting = Meeting(
        title=request.title,
        transcript=request.transcript,
        summary=extraction.summary,
        participants=extraction.participants,
    )
    db.add(meeting)
    await db.flush()
    
    # Save general risks 
    for risk in extraction.general_risks:
        db.add(Risk(
            meeting_id=meeting.id,
            description=risk.description,
            related_to="general",
            severity=risk.severity,
        ))
    
    # Save action items with their risks
    for item in extraction.action_items:
        action_item = ActionItem(
            meeting_id=meeting.id,
            description=item.description,
            owner=item.owner,
            due_date=item.due_date,
            priority=item.priority,
        )
        db.add(action_item)
        await db.flush()
        
        for risk in item.risks:
            action_risk = Risk(
                meeting_id=meeting.id,
                description=risk.description,
                related_to=f"action: {item.description}",
                severity=risk.severity,
            )
            db.add(action_risk)
            action_item.risks.append(action_risk)
    
    # Save decisions with their risks
    for decision in extraction.decisions:
        decision_obj = Decision(
            meeting_id=meeting.id,
            description=decision.description,
            made_by=decision.made_by,
        )
        db.add(decision_obj)
        await db.flush()
        
        for risk in decision.risks:
            decision_risk = Risk(
                meeting_id=meeting.id,
                description=risk.description,
                related_to=f"decision: {decision.description}",
                severity=risk.severity,
            )
            db.add(decision_risk)
            decision_obj.risks.append(decision_risk)

    # Attach extraction to meeting object so the route can return it for API responce
    meeting.extraction = extraction

    return meeting


async def get_meeting_with_all_data(db: AsyncSession, meeting_id: UUID) -> Meeting | None:
    return await db.get(
        Meeting,
        meeting_id,
        options=[
            selectinload(Meeting.action_items).selectinload(ActionItem.risks),
            selectinload(Meeting.decisions).selectinload(Decision.risks),
            selectinload(Meeting.risks),
        ]
    )
