import json
import time
import sys
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from app.services.extraction import extract_from_transcript
from app.schemas.meeting import MeetingExtraction


def load_dataset() -> list[dict]:
    path = Path(__file__).parent / "golden_dataset.json"
    with open(path) as f:
        return json.load(f)


def evaluate_single(extraction: MeetingExtraction, expected: dict) -> dict[str, bool]:
    checks = {}

    # Action items
    if "action_items_min" in expected:
        checks["action_items_min_count"] = (
            len(extraction.action_items) >= expected["action_items_min"]
        )
    if "action_items_max" in expected:
        checks["action_items_max_count"] = (
            len(extraction.action_items) <= expected["action_items_max"]
        )

    # Action item owners
    expected_owners = expected.get("action_item_owners", [])
    actual_owners = [i.owner or "" for i in extraction.action_items]
    checks["action_item_owners"] = all(
        any(exp.lower() in actual.lower() for actual in actual_owners)
        for exp in expected_owners
    )

    # Decisions
    if "decisions_min" in expected:
        checks["decisions_min_count"] = (
            len(extraction.decisions) >= expected["decisions_min"]
        )
    if "decisions_max" in expected:
        checks["decisions_max_count"] = (
            len(extraction.decisions) <= expected["decisions_max"]
        )

    # Decision keywords
    decision_keywords = expected.get("decision_keywords", [])
    all_decision_text = " ".join(d.description.lower() for d in extraction.decisions)
    if decision_keywords:
        checks["decision_keywords"] = all(
            kw.lower() in all_decision_text for kw in decision_keywords
        )

    # General risks
    if "general_risks_min" in expected:
        checks["general_risks_min_count"] = (
            len(extraction.general_risks) >= expected["general_risks_min"]
        )

    # High severity risk check — looks across ALL risks (nested + general)
    if expected.get("has_high_severity_risk"):
        all_risks = list(extraction.general_risks)
        for item in extraction.action_items:
            all_risks.extend(item.risks)
        for decision in extraction.decisions:
            all_risks.extend(decision.risks)
        checks["has_high_severity_risk"] = any(
            r.severity == "high" for r in all_risks
        )

    # Participants
    expected_participants = expected.get("participants", [])
    actual_participants = [p.lower() for p in extraction.participants]
    checks["participants"] = all(
        ep.lower() in actual_participants for ep in expected_participants
    )

    # Summary length
    min_len = expected.get("summary_min_length", 0)
    checks["summary_length"] = len(extraction.summary.strip()) >= min_len

    return checks


async def run_eval():
    dataset = load_dataset()
    results = []
    total_checks = 0
    passed_checks = 0

    print(f"\n{'='*60}")
    print(f"MeetMind Prompt Evaluation — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Model: claude-sonnet-4-20250514")
    print(f"Cases: {len(dataset)}")
    print(f"{'='*60}\n")

    for case in dataset:
        print(f"▶ {case['id']}")
        print(f"  {case.get('description', '')}")
        start = time.time()

        try:
            extraction = await extract_from_transcript(case["transcript"])
            latency = round(time.time() - start, 2)
            checks = evaluate_single(extraction, case["expected"])

            case_passed = sum(checks.values())
            case_total = len(checks)
            case_score = round(case_passed / case_total * 100)

            print(f"  Score: {case_passed}/{case_total} ({case_score}%) — {latency}s")
            for name, passed in checks.items():
                icon = "✓" if passed else "✗"
                print(f"    {icon} {name}")

            if not all(checks.values()):
                print(f"  Summary: {extraction.summary[:120]}")
                print(f"  Action items: {len(extraction.action_items)}")
                print(f"  Decisions: {len(extraction.decisions)}")
                print(f"  General risks: {len(extraction.general_risks)}")

            results.append({
                "id": case["id"],
                "score": case_score,
                "latency": latency,
                "checks": {k: bool(v) for k, v in checks.items()},
            })
            total_checks += case_total
            passed_checks += case_passed

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"id": case["id"], "error": str(e)})

        print()
        await asyncio.sleep(1)  # avoid rate limiting

    overall = round(passed_checks / total_checks * 100) if total_checks else 0
    avg_latency = round(
        sum(r.get("latency", 0) for r in results) / len(results), 2
    )

    print(f"{'='*60}")
    print(f"OVERALL: {passed_checks}/{total_checks} ({overall}%)")
    print(f"AVG LATENCY: {avg_latency}s")
    print(f"{'='*60}\n")

    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "overall_score": overall,
            "avg_latency_seconds": avg_latency,
            "results": results
        }, f, indent=2)

    print(f"Results saved → {output_file}")
    return overall


if __name__ == "__main__":
    score = asyncio.run(run_eval())
    sys.exit(0 if score >= 80 else 1)