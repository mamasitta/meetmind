import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.extraction import extract_from_transcript
from app.rag.retriever import search_similar_chunks


async def run_extract_meeting_data(transcript: str) -> dict:
    extraction = await extract_from_transcript(transcript)
    return extraction.model_dump()


async def run_search_past_meetings(query: str, limit: int, exclude_meeting_id: UUID | None = None) -> dict:
    # real vector similarity search — no db needed, Qdrant handles it
    chunks = await search_similar_chunks(
        query = query,
        limit = limit,
        exclude_meeting_id = exclude_meeting_id
    )

    if not chunks:
        return {
            "found": 0,
            "message": f"No past meetings found related to '{query}'",
            "meetings": []
        }

    # group chunks by meeting so Claude sees organized results
    # multiple chunks from same meeting get merged — cleaner for Claude to read
    meetings: dict[str, dict] = {}
    for chunk in chunks:
        mid = chunk["meeting_id"]
        if mid not in meetings:
            meetings[mid] = {
                "meeting_id": mid,
                "excerpts": [],
                "similarity": chunk["similarity"]
            }
        meetings[mid]["excerpts"].append({
            "text": chunk["content"][:300],
            "similarity": chunk["similarity"]
        })

    return {
        "found": len(meetings),
        "query": query,
        "meetings": list(meetings.values())
    }


def run_assess_overall_risk(action_item_risks: list[str], decision_risks: list[str], general_risks: list[str]) -> dict:
    all_risks = action_item_risks + decision_risks + general_risks
    total = len(all_risks)

    if total == 0:
        level = "low"
        reasoning = "No risks identified in this meeting."
    elif total <= 2:
        level = "medium"
        reasoning = f"{total} risk(s) identified. Review before next sprint."
    elif total <= 5:
        level = "high"
        reasoning = f"{total} risks identified. Immediate attention recommended."
    else:
        level = "critical"
        reasoning = f"{total} risks identified. Escalation required."

    return {
        "overall_risk_level": level,
        "total_risks": total,
        "breakdown": {
            "from_action_items": len(action_item_risks),
            "from_decisions": len(decision_risks),
            "general": len(general_risks)
        },
        "reasoning": reasoning
    }


async def execute_tool(tool_name: str, tool_input: dict, db: AsyncSession, current_meeting_id: UUID | None = None) -> str:
    if tool_name == "extract_meeting_data":
        result = await run_extract_meeting_data(transcript = tool_input["transcript"])

    elif tool_name == "search_past_meetings":
        result = await run_search_past_meetings(
            query = tool_input["query"],
            limit = tool_input.get("limit", 3),
            exclude_meeting_id = current_meeting_id
        )

    elif tool_name == "assess_overall_risk":
        result = run_assess_overall_risk(
            action_item_risks = tool_input.get("action_item_risks", []),
            decision_risks = tool_input.get("decision_risks", []),
            general_risks = tool_input.get("general_risks", [])
        )

    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)