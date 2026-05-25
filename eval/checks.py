from app.schemas.meeting import MeetingExtraction
from eval.models import Check
from eval.keywords import keyword_found


def keywords_check(name: str, keywords: list[str], text: str) -> Check:
    if not keywords:
        return Check(name, passed=True, note="no keywords to validate")

    missing = [kw for kw in keywords if not keyword_found(kw, text)]

    return Check(
        name     = name,
        passed   = not missing,
        expected = keywords,
        actual   = f"missing: {missing}" if missing else "all found",
        note     = f"keywords not found: {missing}" if missing else "all present",
    )


def check_count(name: str, actual: int, expected: dict) -> list[Check]:
    checks = []

    if f"{name}_exact" in expected:
        val = expected[f"{name}_exact"]
        checks.append(Check(
            name     = f"{name}_exact",
            passed   = actual == val,
            expected = val,
            actual   = actual,
        ))
        return checks  # exact overrides min/max

    if f"{name}_min" in expected:
        val = expected[f"{name}_min"]
        checks.append(Check(
            name     = f"{name}_min",
            passed   = actual >= val,
            expected = f">={val}",
            actual   = actual,
        ))
        # min=0 with no max means exactly zero expected
        if val == 0 and f"{name}_max" not in expected and actual > 0:
            checks.append(Check(
                name     = f"{name}_zero_enforced",
                passed   = False,
                expected = 0,
                actual   = actual,
                note     = f"expected zero {name}",
            ))

    if f"{name}_max" in expected:
        val = expected[f"{name}_max"]
        checks.append(Check(
            name     = f"{name}_max",
            passed   = actual <= val,
            expected = f"<={val}",
            actual   = actual,
        ))

    return checks


def check_owners(action_items: list, expected_owners: list) -> Check:
    actual_owners = [i.owner for i in action_items if i.owner]

    if not expected_owners:
        return Check("owners", passed=True, note="no owners expected")

    # [None] means we expect action items but with NO owners
    if expected_owners == [None]:
        wrong = bool(actual_owners)
        return Check(
            "owners",
            passed   = not wrong,
            expected = "no owners",
            actual   = actual_owners or "none",
            note     = "owners found when none expected" if wrong else "correct",
        )

    expected_lower = [str(e).lower() for e in expected_owners]
    actual_lower   = [str(a).lower() for a in actual_owners]
    missing        = [e for e in expected_lower if not any(e in a or a in e for a in actual_lower)]

    return Check(
        "owners",
        passed   = not missing,
        expected = expected_owners,
        actual   = actual_owners,
        note     = f"missing: {missing}" if missing else "all found",
    )


def check_participants(actual: list[str], expected: list[str]) -> Check:
    if not expected:
        return Check("participants", passed=True, note="none expected")

    actual_lower = [p.lower() for p in actual]
    missing      = [p for p in expected if p.lower() not in actual_lower]

    return Check(
        "participants",
        passed   = not missing,
        expected = expected,
        actual   = actual,
        note     = f"missing: {missing}" if missing else "all found",
    )


def check_summary(summary: str, expected: dict) -> list[Check]:
    checks = []

    if "summary_min_length" in expected:
        length = len(summary.strip())
        checks.append(Check(
            "summary_length",
            passed   = length >= expected["summary_min_length"],
            expected = f">={expected['summary_min_length']} chars",
            actual   = f"{length} chars",
        ))

    if "summary_keywords" in expected:
        checks.append(keywords_check("summary_keywords", expected["summary_keywords"], summary))

    return checks


def check_risks(extraction: MeetingExtraction, expected: dict) -> list[Check]:
    # gather all risks from everywhere in the extraction
    all_risks = list(extraction.general_risks)
    for item in extraction.action_items:
        all_risks.extend(item.risks)
    for decision in extraction.decisions:
        all_risks.extend(decision.risks)

    checks = []

    if "has_high_severity_risk" in expected:
        found = any(r.severity == "high" for r in all_risks)
        checks.append(Check(
            "has_high_severity_risk",
            passed   = found,
            expected = "at least one high severity risk",
            actual   = f"{sum(1 for r in all_risks if r.severity == 'high')} found",
        ))

    if "has_low_severity_risk" in expected:
        found = any(r.severity == "low" for r in all_risks)
        checks.append(Check(
            "has_low_severity_risk",
            passed   = found,
            expected = "at least one low severity risk",
            actual   = f"{sum(1 for r in all_risks if r.severity == 'low')} found",
        ))

    if "has_nested_action_risk" in expected:
        found = any(len(item.risks) > 0 for item in extraction.action_items)
        checks.append(Check(
            "has_nested_action_risk",
            passed   = found,
            expected = "risks nested inside action items",
            actual   = "found" if found else "none",
        ))

    if "has_nested_decision_risk" in expected:
        found = any(len(d.risks) > 0 for d in extraction.decisions)
        checks.append(Check(
            "has_nested_decision_risk",
            passed   = found,
            expected = "risks nested inside decisions",
            actual   = "found" if found else "none",
        ))

    return checks


def check_due_dates(extraction: MeetingExtraction, expected: dict) -> list[Check]:
    if "due_date_extracted" not in expected:
        return []

    found = any(item.due_date for item in extraction.action_items)
    dates = [item.due_date for item in extraction.action_items if item.due_date]

    return [Check(
        "due_date_extracted",
        passed   = found,
        expected = "at least one due date",
        actual   = dates if dates else "none",
    )]