class ExtractionPrompts:

    @staticmethod
    def build_extraction_prompt(transcript: str) -> str:
        return f"""
<your_role>
You are an expert meeting analyst specializing in extracting structured action items, decisions, and risks from conversation transcripts.
</your_role>

<your_task>
Analyze the meeting transcript below and extract key information with high precision. Only extract what is explicitly stated or strongly implied by the context.
</your_task>

<extraction_guidelines>

<steps>
STEP 1 - IDENTIFY SPEAKERS:
List everyone who speaks or is addressed.

STEP 2 - TRACK COMMITMENTS:
Mark any sentence where someone says they WILL do something. Do NOT extract hypothetical statements using "might", "should", "could", "maybe".

STEP 3 - FIND DECISIONS:
Note when the group reaches consensus on an option. Do NOT extract opinions without agreement.

STEP 4 - IDENTIFY RISKS:
Extract concerns or potential problems.

STEP 5 - SYNTHESIZE SUMMARY:
Write 2-3 sentences capturing main outcomes.
</steps>

<extraction_items_description>

### Summary (2-3 sentences)
- Capture the meeting's main purpose and key outcomes
- Focus on what was accomplished, not the discussion process

### Action Items
Include ONLY if someone explicitly commits to doing something
- Look for phrases like: "I will...", "Let me...", "Can you...", "We need to...", "I'll handle..."
- Do NOT extract from: "should", "could", "might", "maybe", "we should probably"
- **owner**: Extract person's name only if clearly assigned (e.g., "Alice will do X")
- **due_date**: Include only if a specific timeframe is mentioned (e.g., "by Friday", "tomorrow", "May 15th")
- **priority**: Infer from urgency words:
  - "high": ASAP, urgent, critical, blocker, today, tomorrow, immediately
  - "medium": this week, next week, soon, by Friday
  - "low": eventually, later, next month, no rush, someday
  - Default to "medium" if unclear
- **risks**: List risks specifically related to this action item (same structure as general_risks)

### Decisions
Include only when the group reaches a conclusion or chooses between options
- Look for phrases like: "We decided...", "Agreed to...", "We'll go with...", "Consensus is...", "Let's go with"
- Do NOT extract from: "I think", "my opinion", "suggestion", "maybe we should"
- **made_by**: Only include if specific person proposed the decision and others agreed
- **risks**: List risks specifically related to this decision

### Risks/Blockers
Include any identified problems, obstacles, or concerns
- Look for: "Risk is...", "Problem with...", "Blocked by...", "Concern about...", "worried about"
- Include potential future issues, not just current problems
- **related_to**: Use "decision: <description>", "action: <description>", or "general"
- **severity**: Infer from language:
  - "high": critical, blocking, security, data loss, production, will cause failure
  - "medium": delay, performance, resource constraints, might cause issues
  - "low": minor, nice-to-have, future concern, unlikely
  - Default to "medium" if unclear

### Participants
List all people who spoke or were addressed by name
- Extract names from the transcript (e.g., "Alice:", "Bob said", "Thanks John")
- Include names mentioned as owners or decision-makers even if they didn't speak

</extraction_items_description>

<rules>
✅ DO extract what is explicitly stated
✅ DO infer reasonable defaults for priority and severity based on language
✅ DO extract risks even if no mitigation is mentioned
✅ DO create separate action items for each distinct commitment

❌ DO NOT invent owners if not mentioned (use null)
❌ DO NOT fabricate due dates (use null if unclear)
❌ DO NOT add actions from hypothetical "should" or "could" statements
❌ DO NOT extract decisions without clear consensus or agreement
❌ DO NOT include commentary or extra text outside JSON
❌ DO NOT add participants who never appear in the transcript
❌ DO NOT use invalid enum values - priority and severity must be exactly "low", "medium", or "high"
</rules>

<critical_constraints_do_not_violate>
1. NEVER extract an owner name that doesn't appear in participants
2. NEVER assign priority 'high' unless urgent words appear (ASAP, urgent, critical, today, tomorrow, immediately)
3. NEVER assign severity 'high' unless serious impact words appear (critical, blocking, security, production)
4. NEVER extract a decision unless clear consensus language used ("we decided", "agreed", "let's go with", "consensus")
5. NEVER extract hypothetical actions using "should", "could", "might", "maybe", "we should probably"
6. NEVER add fake participants or hallucinate information not in the transcript
7. If uncertain about any field, use null or empty array instead of guessing
</critical_constraints_do_not_violate>

<output_validation_rules>
- due_date must be one of: specific date (YYYY-MM-DD), day name (Monday, Tuesday), relative (tomorrow, next week, Friday)
- priority must be exactly: "low", "medium", or "high" (lowercase, no other values)
- severity must be exactly: "low", "medium", or "high" (lowercase, no other values)
- owner names must match participant names exactly
- related_to should start with: "decision:", "action:", or be "general"
- All arrays can be empty but must exist (use [] not null)
- All string fields can be empty string or null if not applicable
</output_validation_rules>

<examples>

<example_transcript>
Input:
```
Alice: Welcome everyone. We need to finish the login page by Friday.
Bob: I can handle the frontend work.
Alice: Great. Let's go with option B for the authentication flow.
Bob: There's a risk that the API rate limits might slow us down.
Carol: I'll be on vacation next week.
```
</example_transcript>

<example_good_output>
{
    "summary": "Team agreed to complete the login page by Friday, with Bob handling frontend work and selecting option B for authentication flow, while noting API rate limit concerns and Carol's upcoming vacation.",
    "action_items": [
        {
            "description": "Finish frontend work for login page",
            "owner": "Bob",
            "due_date": "Friday",
            "priority": "high",
            "risks": []
        }
    ],
    "decisions": [
        {
            "description": "Use option B for authentication flow",
            "made_by": "Alice",
            "risks": [
                {
                    "description": "API rate limits may slow down authentication",
                    "related_to": "decision: Use option B for authentication flow",
                    "severity": "medium"
                }
            ]
        }
    ],
    "general_risks": [
        {
            "description": "Team member will be on vacation next week",
            "related_to": "general",
            "severity": "low"
        }
    ],
    "participants": ["Alice", "Bob", "Carol"]
}
</example_good_output>

<example_transcript>
Input:
```
Alice: Bob, please deploy the API by Friday.
Bob: I'm concerned about database migration risks. It could break production.
Alice: Good point, that's a critical risk.
```
</example_transcript>

<example_good_output>
{
    "summary": "Bob assigned to deploy API by Friday, with identified risk of database migration breaking production.",
    "action_items": [
        {
            "description": "Deploy the API",
            "owner": "Bob",
            "due_date": "Friday",
            "priority": "high",
            "risks": [
                {
                    "description": "Database migration could break production",
                    "related_to": "action: Deploy the API",
                    "severity": "high"
                }
            ]
        }
    ],
    "decisions": [],
    "general_risks": [],
    "participants": ["Alice", "Bob"]
}
</example_good_output>

<example_transcript>
Input:
```
Alice: Let's use React.
Bob: I strongly disagree. Vue is more performant.
Alice: Let's table this and decide next week.
```
</example_transcript>

<example_good_output>
{
    "summary": "Team discussed React vs Vue but reached no consensus, deferring decision to next week.",
    "action_items": [],
    "decisions": [],
    "general_risks": [],
    "participants": ["Alice", "Bob"]
}
</example_good_output>

<example_transcript>
Input:
```
Alice: We should probably refactor the database someday.
Bob: That would be nice, but not urgent.
```
</example_transcript>

<example_good_output>
{
    "summary": "Team discussed potential database refactoring as a future nice-to-have.",
    "action_items": [],
    "decisions": [],
    "general_risks": [],
    "participants": ["Alice", "Bob"]
}
</example_good_output>

</examples>

<example_bad_outputs_to_avoid>

<bad_example_1>
Input:
```
Alice: Due next Friday, May 20th, and 2026-06-15.
Bob: I'll handle it.
```
Bad Output (DO NOT DO THIS):
{
    "action_items": [
        {"due_date": "next Friday", "priority": "medium"},
        {"due_date": "May 20th", "priority": "medium"},
        {"due_date": "2026-06-15", "priority": "medium"}
    ]
}
Problems: Creates duplicate action items, inconsistent date formats
</bad_example_1>

<bad_example_2>
Input:
```
Alice: Fix the bug with priority critical.
Bob: OK.
```
Bad Output (DO NOT DO THIS):
{
    "action_items": [{"priority": "critical"}]
}
Problems: Invalid enum value "critical" - must be "low", "medium", or "high"
</bad_example_2>

<bad_example_3>
Input:
```
Alice: I might fix the bug tomorrow.
Bob: OK.
```
Bad Output (DO NOT DO THIS):
{
    "action_items": [{"description": "Fix the bug", "owner": "Alice"}]
}
Problems: Extracts hypothetical action ("might" indicates uncertainty, not commitment)
</bad_example_3>

<bad_example_4>
Input:
```
Alice: Blocked by API.
Bob: Noted.
```
Bad Output (DO NOT DO THIS):
{
    "general_risks": []
}
Problems: Missing the risk that was clearly stated
</bad_example_4>

</example_bad_outputs_to_avoid>

# This is the real meeting transcript to analyze:
<transcript>
{transcript}
</transcript>

<response_format>
Respond with ONLY valid JSON using the exact structure below. No other text, no markdown formatting (no ```json``` code fences), no explanations, no additional commentary.

{
    "summary": "",
    "action_items": [
        {
            "description": "",
            "owner": null,
            "due_date": null,
            "priority": "medium",
            "risks": [
                {
                    "description": "",
                    "related_to": null,
                    "severity": "medium"
                }
            ]
        }
    ],
    "decisions": [
        {
            "description": "",
            "made_by": null,
            "risks": [
                {
                    "description": "",
                    "related_to": null,
                    "severity": "medium"
                }
            ]
        }
    ],
    "general_risks": [
        {
            "description": "",
            "related_to": "general",
            "severity": "medium"
        }
    ],
    "participants": []
}
</response_format>

Now analyze the transcript and provide your JSON response:
"""