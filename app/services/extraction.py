import json
from anthropic import Anthropic
from app.core.config import settings
from app.schemas.meeting import MeetingExtraction, ActionItem, Decision, Risk
from app.prompts.extraction_prompts import ExtractionPrompts


# One client instance, reused for all requests
client = Anthropic(api_key=settings.anthropic_api_key)



def extract_from_transcript(transcript: str) -> MeetingExtraction:
    
    # Call Claude
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": ExtractionPrompts.build_extraction_prompt(transcript)
            }
        ]
    )

    # Get the text response
    # response.content is a list of blocks — we want the first text block
    raw_text = response.content[0].text

    # Parse JSON
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\nRaw response: {raw_text}")

    # Validate with Pydantic
    extraction = MeetingExtraction(**data)

    return extraction
