from app.agents.tools.tool_definition_helpers import ToolDefinitions


class AnalysisPrompts:
    """System prompts for meeting analysis with tool calling"""
    
    @classmethod
    def get_system_prompt(cls) -> str:
        tools_desc = ToolDefinitions.get_tools_description()
        
        return f"""
            You are a meeting analyst. Extract insights and return ONLY a JSON object.

            TOOLS:
            {tools_desc}

            WORKFLOW:
            1. Call extract_meeting_data
            2. Call search_past_meetings for key topics
            3. Call assess_overall_risk if risks found
            4. Return FINAL JSON (no other text)

            FINAL JSON MUST BE EXACTLY:
            {{
                "executive_summary": "2-3 sentences about key outcomes",
                "key_findings": ["finding 1", "finding 2"],
                "historical_context": "What past meetings show, or 'No relevant history'",
                "overall_risk_level": "low|medium|high|critical",
                "recommended_actions": ["action 1", "action 2"],
                "follow_up_required": true
            }}

            RULES:
            - Return ONLY the JSON. No other text.
            - Do NOT put JSON inside the executive_summary string.
            - Do NOT explain your reasoning.
            - Do NOT add markdown or code blocks.
            - executive_summary must be plain text, not a JSON string.

            Example CORRECT response:
            {{
                "executive_summary": "Bob will finish login page by Thursday. Team chose Stripe for payments. Sandbox outage is blocking release.",
                "key_findings": ["Bob committed to Thursday deadline", "Stripe sandbox outage is critical blocker"],
                "historical_context": "No relevant history found",
                "overall_risk_level": "high",
                "recommended_actions": ["Carol to contact Stripe support today", "Bob to complete login page by Thursday"],
                "follow_up_required": true
            }}

            Now analyze the transcript and return ONLY the JSON object.
            """
    
    @classmethod
    def get_tool_description(cls) -> str:
        """Return description of available tools (delegates to ToolDefinitions)"""
        return ToolDefinitions.get_tools_description()
    
    @classmethod
    def get_tools(cls):
        """Return tool definitions for Claude function calling"""
        return ToolDefinitions.get_tools()