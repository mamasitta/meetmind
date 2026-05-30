AGENT_TOOLS = [
    {
        "name": "extract_meeting_data",
        "description": (
            "Extract structured data from a meeting transcript. "
            "Returns action items with owners and priorities, decisions with risk assessments, "
            "general risks, participants list, and a summary. "
            "Always call this first when processing a new transcript."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "The full meeting transcript text to analyze"
                }
            },
            "required": ["transcript"]
        }
    },
    {
        "name": "search_past_meetings",
        "description": (
            "Search the knowledge base of past meetings for related topics, decisions, or action items. "
            "Use this to find historical context relevant to the current meeting. "
            "For example if the current meeting mentions Stripe, search for 'Stripe' "
            "to find past decisions or blockers on the same topic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Topic, decision, or person name to search for in past meetings"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return, default 3, max 5",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "assess_overall_risk",
        "description": (
            "Calculate an overall risk assessment for the meeting based on all extracted risks. "
            "Call this after extract_meeting_data when the meeting contains risks or blockers. "
            "Returns an overall risk level (low/medium/high/critical) with reasoning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action_item_risks": {
                    "type": "array",
                    "description": "Risk descriptions from action items",
                    "items": {"type": "string"}
                },
                "decision_risks": {
                    "type": "array",
                    "description": "Risk descriptions from decisions",
                    "items": {"type": "string"}
                },
                "general_risks": {
                    "type": "array",
                    "description": "General risk descriptions",
                    "items": {"type": "string"}
                }
            },
            "required": ["action_item_risks", "decision_risks", "general_risks"]
        }
    }
]