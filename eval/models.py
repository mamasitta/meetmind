from dataclasses import dataclass
from typing import Optional
from eval.config import SEVERITY_WEIGHTS


@dataclass
class Check:
    name:     str
    passed:   bool
    expected: object = None
    actual:   object = None
    note:     str    = ""


@dataclass
class CaseResult:
    id:          str
    description: str
    severity:    str
    passed:      bool
    score:       float
    checks:      list[Check]
    latency:     float
    summary:     str
    error:       Optional[str] = None


@dataclass
class Report:
    timestamp: str
    model:     str
    results:   list[CaseResult]

    @property
    def total(self):         return len(self.results)
    @property
    def passed(self):        return sum(1 for r in self.results if r.passed)
    @property
    def failed(self):        return self.total - self.passed
    @property
    def avg_latency(self):   return sum(r.latency for r in self.results) / self.total if self.total else 0
    @property
    def total_checks(self):  return sum(len(r.checks) for r in self.results)
    @property
    def passed_checks(self): return sum(sum(1 for c in r.checks if c.passed) for r in self.results)

    @property
    def overall_score(self):
        return sum(r.score for r in self.results) / self.total if self.total else 0

    @property
    def weighted_score(self):
        total_w = weighted = 0.0
        for r in self.results:
            w         = SEVERITY_WEIGHTS.get(r.severity, 0.5)
            total_w  += w
            weighted += (r.score / 100) * w
        return (weighted / total_w * 100) if total_w else 0