from app.models.meeting import Meeting as MeetingModel
from app.schemas.meeting import MeetingResponse, MeetingExtraction, Risk, ActionItem, Decision



def meeting_to_response(meeting: MeetingModel) -> MeetingResponse:
    """Convert database Meeting model to API response schema"""
    
    # Build extraction from stored data
    extraction = MeetingExtraction(
        summary=meeting.summary or "",
        action_items=[
            ActionItem(
                description=item.description,
                owner=item.owner,
                due_date=item.due_date,
                priority=item.priority,
                risks=[
                    Risk(
                        description=risk.description,
                        related_to=risk.related_to,
                        severity=risk.severity
                    )
                    for risk in item.risks
                ]
            )
            for item in meeting.action_items
        ],
        decisions=[
            Decision(
                description=decision.description,
                made_by=decision.made_by,
                risks=[
                    Risk(
                        description=risk.description,
                        related_to=risk.related_to,
                        severity=risk.severity
                    )
                    for risk in decision.risks
                ]
            )
            for decision in meeting.decisions
        ],
        general_risks=[
            Risk(
                description=risk.description,
                related_to=risk.related_to,
                severity=risk.severity
            )
            for risk in meeting.risks 
            if risk.related_to == "general"
        ],
        participants=meeting.participants or [],
    )
    
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        created_at=meeting.created_at,
        extraction=extraction
    )