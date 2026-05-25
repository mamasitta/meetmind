import json
from datetime import datetime
from eval.models import Report
from eval.config import PASS_THRESHOLD


def build_html(report: Report) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cards = ""
    for r in report.results:
        color  = "#d4edda" if r.score >= 90 else "#fff3cd" if r.score >= PASS_THRESHOLD else "#f8d7da"
        checks = ""
        for c in r.checks:
            bg  = "#d4edda" if c.passed else "#f8d7da"
            ico = "✅" if c.passed else "❌"
            checks += f"""
            <div style="padding:8px;border-radius:6px;background:{bg};border-left:3px solid {'#28a745' if c.passed else '#dc3545'}">
                <strong>{ico} {c.name}</strong><br>
                Expected: {c.expected} &nbsp;|&nbsp; Actual: {c.actual}<br>
                <small>{c.note}</small>
            </div>"""

        error_block = (
            f"<pre style='background:#2d2d2d;color:#f8f8f2;padding:12px;border-radius:6px;font-size:.8em'>{r.error}</pre>"
            if r.error else ""
        )

        cards += f"""
        <div style="background:white;border-radius:12px;margin-bottom:24px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)">
            <div style="padding:18px 20px;background:{color};display:flex;justify-content:space-between;align-items:center">
                <div>
                    <strong>{r.id}</strong>
                    <span style="color:#555;font-size:.9em;margin-left:10px">{r.description}</span>
                </div>
                <div style="font-weight:bold">{r.score}% ({sum(1 for c in r.checks if c.passed)}/{len(r.checks)}) &nbsp; {r.latency}s</div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px;padding:16px;background:#f8f9fa">
                {checks}
            </div>
            <div style="padding:16px;border-top:1px solid #e0e0e0">
                <strong style="color:#667eea">Claude's summary</strong>
                <pre style="background:#2d2d2d;color:#f8f8f2;padding:12px;border-radius:6px;margin-top:8px;white-space:pre-wrap;font-size:.85em">{r.summary[:400] or "N/A"}</pre>
                {error_block}
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MeetMind Eval Report</title>
<style>
  * {{ margin:0;padding:0;box-sizing:border-box }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
          background:linear-gradient(135deg,#667eea,#764ba2);padding:20px }}
  .wrap {{ max-width:1400px;margin:0 auto }}
  .stat {{ background:white;padding:24px;border-radius:12px;text-align:center;box-shadow:0 2px 4px rgba(0,0,0,.1) }}
  .val  {{ font-size:2.2em;font-weight:bold;background:linear-gradient(135deg,#667eea,#764ba2);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent }}
  .lbl  {{ color:#666;margin-top:6px }}
</style>
</head>
<body>
<div class="wrap">
  <div style="background:white;padding:36px;border-radius:16px;text-align:center;margin-bottom:28px;box-shadow:0 4px 6px rgba(0,0,0,.1)">
    <h1 style="font-size:2.2em;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
      MeetMind Eval Report
    </h1>
    <p style="color:#888;margin-top:6px">{timestamp} &nbsp;|&nbsp; {report.model}</p>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:28px">
    <div class="stat"><div class="val">{report.overall_score:.1f}%</div><div class="lbl">Overall Score</div></div>
    <div class="stat"><div class="val">{report.weighted_score:.1f}%</div><div class="lbl">Weighted Score</div></div>
    <div class="stat"><div class="val">{report.passed}/{report.total}</div><div class="lbl">Tests Passed</div></div>
    <div class="stat"><div class="val">{report.passed_checks}/{report.total_checks}</div><div class="lbl">Checks Passed</div></div>
    <div class="stat"><div class="val">{report.avg_latency:.1f}s</div><div class="lbl">Avg Latency</div></div>
  </div>

  {cards}
</div>
</body>
</html>"""


def build_json(report: Report) -> str:
    return json.dumps({
        "timestamp":      report.timestamp,
        "model":          report.model,
        "overall_score":  report.overall_score,
        "weighted_score": report.weighted_score,
        "passed":         report.passed,
        "total":          report.total,
        "avg_latency":    report.avg_latency,
        "results": [
            {
                "id":      r.id,
                "score":   r.score,
                "passed":  r.passed,
                "latency": r.latency,
                "checks":  [{"name": c.name, "passed": c.passed, "note": c.note} for c in r.checks],
                "error":   r.error,
            }
            for r in report.results
        ]
    }, indent=2)