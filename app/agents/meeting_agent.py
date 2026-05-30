import json
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.prompts.agent_system_prompt import AnalysisPrompts
from app.agents.tools.executor import execute_tool



client = AsyncAnthropic(api_key=settings.anthropic_api_key)

# safety limit — without this a bug in the loop burns your API credits
MAX_ITERATIONS = 10

SYSTEM_PROMPT = AnalysisPrompts

async def run_meeting_agent(transcript: str, db: AsyncSession) -> dict:
    # start with the user message — Claude reads this and decides what to do first
    messages = [
        {
            "role":    "user",
            "content": f"Please fully analyze this meeting transcript:\n\n{transcript}"
        }
    ]

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f" [agent] iteration {iteration}")

        response = await client.messages.create(
            model = settings.claude_model,
            max_tokens = 4096,
            system = SYSTEM_PROMPT.get_system_prompt(),
            tools = SYSTEM_PROMPT.get_tools(),  # type: ignore[arg-type]
            messages = messages  # type: ignore[arg-type]
        )

        print(f" [agent] stop reason: {response.stop_reason}")

        # Claude finished — extract the final JSON report 
        if response.stop_reason == "end_turn":
            text_block = next(
                (b for b in response.content if hasattr(b, "text")),
                None
            )
            if not text_block:
                raise ValueError("Agent finished but returned no text")

            try:
                return json.loads(text_block.text)
            except json.JSONDecodeError:
                # Claude returned plain text instead of JSON
                return {
                    "executive_summary": text_block.text,
                    "key_findings": [],
                    "historical_context": "Not analyzed",
                    "overall_risk_level": "unknown",
                    "recommended_actions": [],
                    "follow_up_required": False
                }

        # Claude wants to use a tool:
        if response.stop_reason == "tool_use":

            # add Claude's response to history
            # Claude needs to see its own previous messages
            messages.append({
                "role": "assistant",
                "content": response.content  # type: ignore[arg-type]
            })

            # Claude can request multiple tools at once — handle all of them
            tool_blocks = [
                b for b in response.content
                if hasattr(b, "type") and b.type == "tool_use"
            ]

            tool_results = []
            for tool in tool_blocks:
                print(f" [agent] calling tool: {tool.name}")
                print(f" [agent] input: {json.dumps(tool.input)[:200]}")

                result = await execute_tool(
                    tool_name  = tool.name,
                    tool_input = tool.input,
                    db = db
                )

                print(f" [agent] result: {result[:200]}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool.id,   # must match the id Claude sent
                    "content": result
                })

            # send all results back — Claude reads these and continues the loop
            messages.append({
                "role": "user",
                "content": tool_results
            })

            continue

        # unexpected stop reason — something went wrong 
        raise ValueError(f"Unexpected stop reason: {response.stop_reason}")

    raise ValueError(f"Agent exceeded {MAX_ITERATIONS} iterations — possible loop")