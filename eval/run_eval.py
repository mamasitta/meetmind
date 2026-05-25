#!/usr/bin/env python3
"""
MeetMind prompt evaluation entry point.

Usage:
    python -m eval.run_eval
"""

import json
import sys
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

# add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from eval.config import DATASET_PATH, RESULTS_DIR, RATE_LIMIT_SEC, SCORE_THRESHOLD
from eval.models import Report
from eval.runner import run_case
from eval.report import build_html, build_json


async def main():
    print(f"\n{'='*60}")
    print(f"MeetMind Eval  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  {settings.claude_model}")
    print(f"{'='*60}\n")

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} cases\n")

    results = []
    for i, case in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] {case['id']}")

        result = await run_case(case)
        results.append(result)

        icon   = "✅" if result.passed else "❌"
        passed = sum(1 for c in result.checks if c.passed)
        print(f"  {icon} {result.score}% ({passed}/{len(result.checks)}) — {result.latency}s")

        failed = [c.name for c in result.checks if not c.passed]
        if failed:
            print(f"  failed: {', '.join(failed)}")
        if result.error:
            print(f"  error:  {result.error[:120]}")

        print()
        await asyncio.sleep(RATE_LIMIT_SEC)

    report = Report(
        timestamp = datetime.now().isoformat(),
        model     = settings.claude_model,
        results   = results,
    )

    print(f"{'='*60}")
    print(f"Score:   {report.overall_score:.1f}%  (weighted: {report.weighted_score:.1f}%)")
    print(f"Passed:  {report.passed}/{report.total} tests")
    print(f"Checks:  {report.passed_checks}/{report.total_checks}")
    print(f"Latency: {report.avg_latency:.2f}s avg")
    print(f"{'='*60}\n")

    # save reports
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = RESULTS_DIR / f"eval_{stamp}.json"
    json_file.write_text(build_json(report), encoding="utf-8")

    html_file = RESULTS_DIR / f"eval_{stamp}.html"
    html_file.write_text(build_html(report), encoding="utf-8")

    print(f"JSON → {json_file}")
    print(f"HTML → {html_file}")

    subprocess.run(["code", "--reuse-window", str(html_file)], capture_output=True, check=False)

    sys.exit(0 if report.overall_score >= SCORE_THRESHOLD else 1)


if __name__ == "__main__":
    asyncio.run(main())