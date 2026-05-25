import time
import traceback
from app.services.extraction import extract_from_transcript
from eval.models import Check, CaseResult
from eval.config import PASS_THRESHOLD
from eval.checks import (
    check_count, check_owners, check_participants,
    check_summary, check_risks, check_due_dates, keywords_check,
)


async def run_case(case: dict) -> CaseResult:
    transcript = case["transcript"]
    expected   = case["expected"]
    start      = time.time()

    try:
        extraction = await extract_from_transcript(transcript)
        latency    = round(time.time() - start, 2)

        # combine text for keyword checks
        all_action_text   = " ".join(i.description for i in extraction.action_items)
        all_decision_text = " ".join(d.description for d in extraction.decisions)
        all_risk_text     = " ".join(r.description for r in extraction.general_risks)

        checks: list[Check] = []

        checks += check_count("action_items",  len(extraction.action_items),  expected)
        checks += check_count("decisions",     len(extraction.decisions),     expected)
        checks += check_count("general_risks", len(extraction.general_risks), expected)

        checks.append(check_owners(extraction.action_items, expected.get("action_item_owners", [])))

        checks.append(keywords_check("action_item_keywords",  expected.get("action_item_keywords",  []), all_action_text))
        checks.append(keywords_check("decision_keywords",     expected.get("decision_keywords",     []), all_decision_text))
        checks.append(keywords_check("general_risk_keywords", expected.get("general_risk_keywords", []), all_risk_text))

        checks.append(check_participants(extraction.participants, expected.get("participants", [])))
        checks += check_summary(extraction.summary, expected)
        checks += check_risks(extraction, expected)
        checks += check_due_dates(extraction, expected)

        passed_n = sum(1 for c in checks if c.passed)
        score    = round(passed_n / len(checks) * 100, 1) if checks else 100.0

        return CaseResult(
            id          = case["id"],
            description = case.get("description", ""),
            severity    = case.get("severity", "medium"),
            passed      = score >= PASS_THRESHOLD,
            score       = score,
            checks      = checks,
            latency     = latency,
            summary     = extraction.summary,
        )

    except Exception as e:
        return CaseResult(
            id          = case["id"],
            description = case.get("description", ""),
            severity    = case.get("severity", "medium"),
            passed      = False,
            score       = 0.0,
            checks      = [],
            latency     = round(time.time() - start, 2),
            summary     = "",
            error       = f"{e}\n{traceback.format_exc()}",
        )