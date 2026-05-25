#!/usr/bin/env python3
"""
MeetMind Claude Evaluation System

A comprehensive evaluation framework for testing Claude's meeting extraction capabilities.
Features:
- Detailed test case management
- Side-by-side comparison reporting
- Score calculation with proper weighting
- HTML and JSON report generation
- Automatic report opening in VS Code
- Rate limiting and error handling
- Semantic keyword matching with synonyms and stemming
"""

import json
import time
import sys
import asyncio
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import traceback

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.services.extraction import extract_from_transcript
from app.schemas.meeting import MeetingExtraction
from app.core.config import settings


# ============================================================================
# Data Models
# ============================================================================

class Severity(Enum):
    """Test case severity levels"""
    CRITICAL = "critical"  # Must pass for deployment
    HIGH = "high"          # Important functionality
    MEDIUM = "medium"      # Nice to have
    LOW = "low"            # Edge cases


@dataclass
class ValidationResult:
    """Individual validation check result"""
    name: str
    passed: bool
    expected: Any = None
    actual: Any = None
    message: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "expected": str(self.expected) if self.expected else None,
            "actual": str(self.actual) if self.actual else None,
            "message": self.message
        }


@dataclass
class TestCaseResult:
    """Complete test case result"""
    id: str
    description: str
    severity: Severity
    passed: bool
    score: float
    passed_checks: int
    total_checks: int
    validations: List[ValidationResult]
    latency_seconds: float
    transcript_preview: str
    claude_output: Dict[str, Any]
    expected: Dict[str, Any]
    error: Optional[str] = None
    traceback: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "severity": self.severity.value,
            "passed": self.passed,
            "score": self.score,
            "passed_checks": self.passed_checks,
            "total_checks": self.total_checks,
            "validations": [v.to_dict() for v in self.validations],
            "latency_seconds": self.latency_seconds,
            "transcript_preview": self.transcript_preview,
            "claude_output": self.claude_output,
            "expected": self.expected,
            "error": self.error
        }


@dataclass
class EvaluationSummary:
    """Overall evaluation summary"""
    timestamp: str
    model: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    overall_score: float
    total_checks: int
    passed_checks: int
    avg_latency_seconds: float
    results: List[TestCaseResult]
    
    @property
    def weighted_score(self) -> float:
        """Calculate weighted score based on severity"""
        if not self.results:
            return 0.0
        
        weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.8,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.3
        }
        
        total_weight = 0
        weighted_score = 0
        
        for result in self.results:
            weight = weights[result.severity]
            total_weight += weight
            weighted_score += (result.score / 100) * weight
        
        return (weighted_score / total_weight * 100) if total_weight > 0 else 0


# ============================================================================
# Semantic Keyword Matcher (NEW)
# ============================================================================

class SemanticMatcher:
    """Handles flexible keyword matching with synonyms and stemming"""
    
    # Synonym dictionary for common variations
    SYNONYMS = {
        # Decision-related
        "table": ["table", "defer", "postpone", "delay", "put off", "hold", "tabled", "deferred"],
        "defer": ["defer", "postpone", "delay", "table", "put off", "hold", "deferred", "tabled"],
        "postpone": ["postpone", "defer", "delay", "table", "put off", "hold", "postponed"],
        "consensus": ["consensus", "agreement", "unanimous", "agreed", "concurrence"],
        
        # Technology
        "kubernetes": ["kubernetes", "k8s", "kube", "k8", "kubernet"],
        "k8s": ["kubernetes", "k8s", "kube", "k8"],
        "aws": ["aws", "amazon web services", "amazon"],
        "postgresql": ["postgresql", "postgres", "pg"],
        "mysql": ["mysql", "my sql"],
        
        # Action-related
        "optimize": ["optimiz", "optimize", "optimized", "optimizing", "optimization", "improve"],
        "optimizing": ["optimiz", "optimize", "optimized", "optimizing", "optimization", "improve"],
        "migrate": ["migrat", "migrate", "migrated", "migrating", "migration", "move", "moving"],
        "deploy": ["deploy", "deployed", "deploying", "deployment", "release", "ship"],
        "schedule": ["schedule", "scheduled", "scheduling", "plan", "arrange", "set up"],
        "handle": ["handle", "handling", "managed", "manage", "take care"],
        
        # Risk-related
        "block": ["block", "blocking", "blocked", "blocker", "stuck", "prevent"],
        "critical": ["critical", "urgent", "blocking", "severe", "production", "p0"],
        "minor": ["minor", "small", "low", "insignificant", "trivial"],
        "payment": ["payment", "payments", "transaction", "billing", "charge"],
        "transactions": ["transaction", "transactions", "payment", "payments", "billing"],
        "break": ["break", "broken", "failing", "fail", "crash", "down"],
        
        # Summary keywords
        "outcome": ["outcome", "result", "conclusion", "resolution", "decision"],
        "update": ["update", "status", "progress", "report", "sync"],
        "discuss": ["discuss", "talk", "review", "cover", "address", "consider"],
        "wiki": ["wiki", "documentation", "docs", "knowledge base", "confluence"],
        "document": ["document", "doc", "documentation", "write up", "writeup"],
        "python 3.12": ["python 3.12", "python3.12", "python 3", "3.12", "py3.12"],
        "python": ["python", "py", "python3", "python 3.12"],

        
        
        # eval_005 specific
        "next week": ["next week", "following week", "coming week"],
        "no consensus": ["no consensus", "no agreement", "disagreement", "divided", "stalled"],

        # For eval_008
        "renewal": ["renewal", "renew", "renewing", "renewed", "extend", "update certificate"],
        "certificate": ["certificate", "cert", "ssl", "tls", "encryption"],
        
        # For eval_009
        "wiki": ["wiki", "documentation", "docs", "knowledge base", "confluence", "readme"],
        
        # eval_012 specific
        "deadline": ["deadline", "end-of-week", "due", "timeframe", "target date", "completion date", "due date"],
        "uncertain": ["uncertain", "unsure", "tentative", "hesitant", "weak commitment", "not committed", "try", "attempt"],
        "report": ["report", "document", "paper", "file", "summary", "memo"],
        "urgent": ["urgent", "critical", "asap", "immediate", "pressing", "high priority"],
        "tentative": ["tentative", "uncertain", "unsure", "hesitant", "not committed"],

        # eval_017 specific
        "ssl": ["ssl", "certificate", "tls", "encryption"],
        "certificate": ["certificate", "ssl", "tls", "cert"],

        # For eval_019
        "upgrade": ["upgrade", "migrate", "update", "move to", "transition"],
        "python": ["python", "python 3.12", "py", "python3"],
        
        # For eval_023
        "optimize": ["optimize", "optimizing", "optimized", "optimization", "improve", "tune"],
        "eod": ["eod", "end of day", "today", "close of business", "cob"],
        
        # For eval_025
        "rate limiting": ["rate limiting", "rate limit", "throttling", "api limit", "quota"],
        
        # General
        "staging": ["staging", "test", "sandbox", "development", "dev"],
        "database": ["database", "db", "data store", "sql"],
        "api": ["api", "endpoint", "service", "interface"],
    }
    
    @staticmethod
    def stem(word: str) -> str:
        """Simple stemming for English words"""
        word = word.lower()
        
        # Remove common suffixes
        suffixes = [
            ('ing', ''), ('ed', ''), ('s', ''), ('es', ''),
            ('er', ''), ('tion', 't'), ('ize', ''), ('ise', ''),
            ('able', ''), ('ible', '')
        ]
        
        for suffix, replacement in suffixes:
            if word.endswith(suffix):
                return word[:-len(suffix)] + replacement
        
        return word
    
    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        return text
    
    @classmethod
    def keyword_matches(cls, keyword: str, text: str) -> bool:
        """
        Check if keyword matches text using synonyms and stemming
        
        Priority order:
        1. Exact match (case-insensitive)
        2. Synonym match
        3. Stemmed match
        """
        normalized_text = cls.normalize(text)
        keyword_lower = keyword.lower()
        
        # 1. Exact match
        if keyword_lower in normalized_text:
            return True
        
        # 2. Synonym match
        if keyword_lower in cls.SYNONYMS:
            for synonym in cls.SYNONYMS[keyword_lower]:
                if synonym in normalized_text:
                    return True
        
        # 3. Stemmed match
        stemmed_keyword = cls.stem(keyword_lower)
        words = normalized_text.split()
        for word in words:
            if cls.stem(word) == stemmed_keyword:
                return True
        
        return False
    
    @classmethod
    def validate_keywords(cls, text: str, expected_keywords: List[str]) -> ValidationResult:
        """Validate that all expected keywords are present in text"""
        
        if not expected_keywords:
            return ValidationResult(
                name="keywords",
                passed=True,
                message="No keywords to validate"
            )
        
        if not text:
            return ValidationResult(
                name="keywords",
                passed=False,
                expected=expected_keywords,
                actual="Empty text",
                message=f"Expected keywords {expected_keywords} but text is empty"
            )
        
        missing = []
        for keyword in expected_keywords:
            if not cls.keyword_matches(keyword, text):
                missing.append(keyword)
        
        if missing:
            return ValidationResult(
                name="keywords",
                passed=False,
                expected=expected_keywords,
                actual=f"Missing: {missing}",
                message=f"Keywords not found: {missing}"
            )
        
        return ValidationResult(
            name="keywords",
            passed=True,
            expected=expected_keywords,
            actual="All found",
            message="All expected keywords present"
        )


# ============================================================================
# Validation Logic (UPDATED with semantic matching)
# ============================================================================

class Validator:
    """Handles all validation logic for meeting extraction"""
    
    @staticmethod
    def validate_count(
        actual: int,
        expected: Dict[str, Any],
        entity_name: str
    ) -> List[ValidationResult]:
        """Validate count expectations"""
        results = []
        
        exact_key = f"{entity_name}_exact"
        min_key = f"{entity_name}_min"
        max_key = f"{entity_name}_max"
        
        # Exact match
        if exact_key in expected:
            expected_val = expected[exact_key]
            passed = actual == expected_val
            results.append(ValidationResult(
                name=f"{entity_name}_exact",
                passed=passed,
                expected=expected_val,
                actual=actual,
                message=f"Expected exactly {expected_val}, got {actual}"
            ))
            return results
        
        # Range validation
        has_min = min_key in expected
        has_max = max_key in expected
        
        if has_min:
            min_val = expected[min_key]
            passed = actual >= min_val
            results.append(ValidationResult(
                name=f"{entity_name}_min",
                passed=passed,
                expected=f"≥{min_val}",
                actual=actual,
                message=f"Expected at least {min_val}, got {actual}"
            ))
        
        if has_max:
            max_val = expected[max_key]
            passed = actual <= max_val
            results.append(ValidationResult(
                name=f"{entity_name}_max",
                passed=passed,
                expected=f"≤{max_val}",
                actual=actual,
                message=f"Expected at most {max_val}, got {actual}"
            ))
        
        # Zero enforcement: if min=0 and no max, expect exactly 0
        if has_min and not has_max and expected[min_key] == 0:
            passed = actual == 0
            if actual > 0:
                results.append(ValidationResult(
                    name=f"{entity_name}_zero_enforced",
                    passed=False,
                    expected=0,
                    actual=actual,
                    message=f"Expected 0 {entity_name} (min=0 with no max), got {actual}"
                ))
        
        return results
    
    @staticmethod
    def validate_owners(
        actual_items: List[Any],
        expected_owners: List[Any]
    ) -> ValidationResult:
        """Validate action item owners"""
        
        # Extract actual owners from action items
        actual_owners = [item.owner for item in actual_items if item.owner] if actual_items else []
        
        # Case 1: No action items, no owners expected
        if not actual_items and not expected_owners:
            return ValidationResult(
                name="action_item_owners",
                passed=True,
                expected="No owners (no items)",
                actual="No items",
                message="Correct: No action items extracted"
            )
        
        # Case 2: No action items but owners expected
        if not actual_items and expected_owners:
            return ValidationResult(
                name="action_item_owners",
                passed=False,
                expected=expected_owners,
                actual="No action items",
                message=f"Expected owners {expected_owners} but no action items extracted"
            )
        
        # Case 3: Expected no owners (empty list)
        if not expected_owners:
            if actual_owners:
                return ValidationResult(
                    name="action_item_owners",
                    passed=False,
                    expected="No owners",
                    actual=actual_owners,
                    message=f"Expected no owners but found: {actual_owners}"
                )
            return ValidationResult(
                name="action_item_owners",
                passed=True,
                expected="No owners",
                actual="No owners",
                message="Correct: No owners extracted"
            )
        
        # Case 4: Expected [None] means action items with NO owners
        if expected_owners == [None]:
            if any(actual_owners):
                return ValidationResult(
                    name="action_item_owners",
                    passed=False,
                    expected="Action items with NO owners",
                    actual=actual_owners,
                    message=f"Expected action items with no owners, but found owners: {actual_owners}"
                )
            return ValidationResult(
                name="action_item_owners",
                passed=True,
                expected="No owners",
                actual="No owners",
                message="Correct: Action items have no owners"
            )
        
        # Case 5: Specific owners expected
        # Check if each expected owner appears in actual owners (case-insensitive, with partial matching)
        expected_lower = [str(e).lower() for e in expected_owners]
        actual_lower = [str(a).lower() for a in actual_owners]
        
        missing = []
        for exp in expected_lower:
            found = False
            for act in actual_lower:
                if exp in act or act in exp:
                    found = True
                    break
            if not found:
                missing.append(exp)
        
        if missing:
            return ValidationResult(
                name="action_item_owners",
                passed=False,
                expected=expected_owners,
                actual=actual_owners,
                message=f"Missing owners: {missing}"
            )
        
        return ValidationResult(
            name="action_item_owners",
            passed=True,
            expected=expected_owners,
            actual=actual_owners,
            message="All expected owners found"
        )
    
    @staticmethod
    def validate_keywords(
        items: List[Any],
        expected_keywords: List[str],
        entity_name: str,
        description_field: str = "description"
    ) -> ValidationResult:
        """Validate keywords in extracted items using semantic matching"""
        
        if not expected_keywords:
            return ValidationResult(
                name=f"{entity_name}_keywords",
                passed=True,
                message="No keywords to validate"
            )
        
        if not items:
            return ValidationResult(
                name=f"{entity_name}_keywords",
                passed=False,
                expected=expected_keywords,
                actual="No items",
                message=f"Expected keywords {expected_keywords} but no {entity_name} extracted"
            )
        
        # Combine all descriptions
        all_text = " ".join(
            getattr(item, description_field, "")
            for item in items
        )
        
        # Use semantic matching
        return SemanticMatcher.validate_keywords(all_text, expected_keywords)
    
    @staticmethod
    def validate_summary_keywords(
        summary: str,
        expected_keywords: List[str]
    ) -> ValidationResult:
        """Validate summary keywords using semantic matching"""
        
        if not expected_keywords:
            return ValidationResult(
                name="summary_keywords",
                passed=True,
                message="No keywords to validate"
            )
        
        return SemanticMatcher.validate_keywords(summary, expected_keywords)
    
    @staticmethod
    def validate_participants(
        actual_participants: List[str],
        expected_participants: List[str]
    ) -> ValidationResult:
        """Validate extracted participants"""
        
        if not expected_participants:
            return ValidationResult(
                name="participants",
                passed=True,
                message="No participants to validate"
            )
        
        actual_lower = [p.lower() for p in actual_participants]
        missing = [p for p in expected_participants if p.lower() not in actual_lower]
        
        if missing:
            return ValidationResult(
                name="participants",
                passed=False,
                expected=expected_participants,
                actual=actual_participants,
                message=f"Missing participants: {missing}"
            )
        
        return ValidationResult(
            name="participants",
            passed=True,
            expected=expected_participants,
            actual=actual_participants,
            message="All expected participants found"
        )
    
    @staticmethod
    def validate_summary(
        summary: str,
        expected: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate summary content"""
        results = []
        
        # Check minimum length
        min_length = expected.get("summary_min_length", 0)
        if min_length > 0:
            actual_length = len(summary.strip())
            passed = actual_length >= min_length
            results.append(ValidationResult(
                name="summary_length",
                passed=passed,
                expected=f"≥{min_length} chars",
                actual=f"{actual_length} chars",
                message=f"Summary length: {actual_length} chars"
            ))
        
        # Check keywords using semantic matching
        keywords = expected.get("summary_keywords", [])
        if keywords:
            result = Validator.validate_summary_keywords(summary, keywords)
            results.append(result)
        
        return results
    
    @staticmethod
    def validate_severity_risks(
        extraction: MeetingExtraction,
        expected: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate risk severity classifications"""
        results = []
        
        # Collect all risks from all locations
        all_risks = list(extraction.general_risks)
        for item in extraction.action_items:
            all_risks.extend(item.risks)
        for decision in extraction.decisions:
            all_risks.extend(decision.risks)
        
        # High severity check
        if expected.get("has_high_severity_risk"):
            has_high = any(r.severity == "high" for r in all_risks)
            results.append(ValidationResult(
                name="has_high_severity_risk",
                passed=has_high,
                expected="At least one HIGH severity risk",
                actual=f"{len([r for r in all_risks if r.severity == 'high'])} high severity risks",
                message="No high severity risk found" if not has_high else "High severity risk correctly identified"
            ))
        
        # Low severity check
        if expected.get("has_low_severity_risk"):
            has_low = any(r.severity == "low" for r in all_risks)
            results.append(ValidationResult(
                name="has_low_severity_risk",
                passed=has_low,
                expected="At least one LOW severity risk",
                actual=f"{len([r for r in all_risks if r.severity == 'low'])} low severity risks",
                message="No low severity risk found" if not has_low else "Low severity risk correctly identified"
            ))
        
        # Nested risks
        if expected.get("has_nested_action_risk"):
            has_nested = any(len(item.risks) > 0 for item in extraction.action_items)
            results.append(ValidationResult(
                name="has_nested_action_risk",
                passed=has_nested,
                expected="Risks nested inside action items",
                actual="No nested risks found" if not has_nested else "Nested risks found",
                message="Expected action items to have nested risks but none found" if not has_nested else "Nested risks correctly identified"
            ))
        
        if expected.get("has_nested_decision_risk"):
            has_nested = any(len(decision.risks) > 0 for decision in extraction.decisions)
            results.append(ValidationResult(
                name="has_nested_decision_risk",
                passed=has_nested,
                expected="Risks nested inside decisions",
                actual="No nested risks found" if not has_nested else "Nested risks found",
                message="Expected decisions to have nested risks but none found" if not has_nested else "Nested risks correctly identified"
            ))
        
        return results
    
    @staticmethod
    def validate_due_dates(
        extraction: MeetingExtraction,
        expected: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate due date extraction"""
        results = []
        
        if expected.get("due_date_extracted"):
            has_due_date = any(item.due_date is not None for item in extraction.action_items)
            results.append(ValidationResult(
                name="due_date_extracted",
                passed=has_due_date,
                expected="Due date should be extracted",
                actual="No due date found" if not has_due_date else f"Due date found: {[item.due_date for item in extraction.action_items if item.due_date]}",
                message="Expected action item to have a due date but none found" if not has_due_date else "Due date correctly extracted"
            ))
        
        return results


# ============================================================================
# Evaluation Engine
# ============================================================================

class EvaluationEngine:
    """Main evaluation engine that orchestrates all validations"""
    
    def __init__(self):
        self.validator = Validator()
    
    async def evaluate_case(
        self,
        case: Dict[str, Any],
        transcript: str,
        expected: Dict[str, Any]
    ) -> TestCaseResult:
        """Evaluate a single test case"""
        
        validations = []
        start_time = time.time()
        
        try:
            # Run Claude extraction
            extraction = await extract_from_transcript(transcript)
            latency = round(time.time() - start_time, 2)
            
            # Build Claude output dict for reporting
            claude_output = {
                "summary": extraction.summary,
                "action_items_count": len(extraction.action_items),
                "action_items": [item.description for item in extraction.action_items],
                "action_item_owners": [item.owner for item in extraction.action_items if item.owner],
                "decisions_count": len(extraction.decisions),
                "decisions": [d.description for d in extraction.decisions],
                "general_risks_count": len(extraction.general_risks),
                "general_risks": [r.description for r in extraction.general_risks],
                "participants": extraction.participants,
                "nested_action_risks": [
                    {"description": r.description, "severity": r.severity}
                    for item in extraction.action_items for r in item.risks
                ],
                "nested_decision_risks": [
                    {"description": r.description, "severity": r.severity}
                    for decision in extraction.decisions for r in decision.risks
                ]
            }
            
            # Run all validations
            
            # 1. Count validations
            validations.extend(self.validator.validate_count(
                len(extraction.action_items), expected, "action_items"
            ))
            validations.extend(self.validator.validate_count(
                len(extraction.decisions), expected, "decisions"
            ))
            validations.extend(self.validator.validate_count(
                len(extraction.general_risks), expected, "general_risks"
            ))
            
            # 2. Owner validation
            validations.append(self.validator.validate_owners(
                extraction.action_items,
                expected.get("action_item_owners", [])
            ))
            
            # 3. Keyword validations (NOW USING SEMANTIC MATCHING)
            validations.append(self.validator.validate_keywords(
                extraction.action_items,
                expected.get("action_item_keywords", []),
                "action_item"
            ))
            validations.append(self.validator.validate_keywords(
                extraction.decisions,
                expected.get("decision_keywords", []),
                "decision"
            ))
            validations.append(self.validator.validate_keywords(
                extraction.general_risks,
                expected.get("general_risk_keywords", []),
                "general_risk"
            ))
            
            # 4. Participants validation
            validations.append(self.validator.validate_participants(
                extraction.participants,
                expected.get("participants", [])
            ))
            
            # 5. Summary validation (NOW USING SEMANTIC MATCHING)
            validations.extend(self.validator.validate_summary(
                extraction.summary,
                expected
            ))
            
            # 6. Severity and nested risks validation
            validations.extend(self.validator.validate_severity_risks(
                extraction,
                expected
            ))
            
            # 7. Due date validation
            validations.extend(self.validator.validate_due_dates(
                extraction,
                expected
            ))
            
            # Calculate score
            passed_checks = sum(1 for v in validations if v.passed)
            total_checks = len(validations)
            score = (passed_checks / total_checks * 100) if total_checks > 0 else 100
            
            # Determine severity
            severity_map = {
                "critical": Severity.CRITICAL,
                "high": Severity.HIGH,
                "medium": Severity.MEDIUM,
                "low": Severity.LOW
            }
            severity = severity_map.get(case.get("severity", "medium"), Severity.MEDIUM)
            
            return TestCaseResult(
                id=case["id"],
                description=case.get("description", ""),
                severity=severity,
                passed=score >= 70,  # 70% threshold for passing
                score=score,
                passed_checks=passed_checks,
                total_checks=total_checks,
                validations=validations,
                latency_seconds=latency,
                transcript_preview=transcript[:500] + ("..." if len(transcript) > 500 else ""),
                claude_output=claude_output,
                expected=expected,
                error=None
            )
            
        except Exception as e:
            return TestCaseResult(
                id=case["id"],
                description=case.get("description", ""),
                severity=Severity.MEDIUM,
                passed=False,
                score=0,
                passed_checks=0,
                total_checks=0,
                validations=[],
                latency_seconds=round(time.time() - start_time, 2),
                transcript_preview=transcript[:500] + ("..." if len(transcript) > 500 else ""),
                claude_output={},
                expected=expected,
                error=str(e),
                traceback=traceback.format_exc()
            )


# ============================================================================
# Report Generator
# ============================================================================

class ReportGenerator:
    """Generates HTML and JSON reports"""
    
    @staticmethod
    def generate_html(summary: EvaluationSummary) -> str:
        """Generate beautiful HTML report"""
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Test case purpose descriptions
        test_purposes = {
            "eval_001_clear_commitments": "Tests ability to extract clear action items with explicit owners, decisions, and nested risks.",
            "eval_002_no_decisions": "Tests that Claude does NOT hallucinate decisions or risks when they don't exist.",
            "eval_003_high_severity_risk_general": "Tests extraction of high-severity risks with proper classification.",
            "eval_004_no_hypotheticals": "Tests that hypothetical statements are NOT converted to action items.",
            "eval_005_no_false_consensus": "Tests that disagreements without resolution are NOT extracted as decisions.",
            "eval_006_action_item_with_nested_risk_high": "Tests that risks attached to action items are nested, not general.",
            "eval_007_decision_with_nested_risk_medium": "Tests that risks attached to decisions are nested correctly.",
            "eval_008_multiple_risks_all_types": "Tests handling multiple risk types simultaneously.",
            "eval_009_low_severity_risk": "Tests extraction of low-severity risks.",
            "eval_010_multiple_owners_one_action": "Tests action items with multiple assignees.",
            "eval_011_action_item_without_owner": "Tests action items without explicit owners.",
            "eval_012_ambiguous_due_date": "Tests extraction with vague due dates.",
            "eval_013_risk_mentioned_multiple_times": "Tests duplicate risk prevention.",
            "eval_014_risk_with_implicit_mitigation": "Tests risks mentioned WITH solutions.",
            "eval_015_no_participants_mentioned": "Tests extraction with anonymous speakers.",
            "eval_016_empty_transcript": "Tests graceful handling of empty input.",
            "eval_017_very_long_transcript": "Tests performance with long transcripts.",
            "eval_018_risk_severity_inference_from_words": "Tests severity inference from urgency words.",
            "eval_019_decision_made_by_multiple": "Tests group consensus decisions.",
            "eval_020_action_item_with_implicit_date": "Tests implicit due date inference.",
            "eval_021_cross_referenced_risk": "Tests risks related to both decisions and actions.",
            "eval_022_malformed_speaker_format": "Tests non-standard speaker formatting.",
            "eval_023_no_action_keywords": "Tests commitments without standard keywords.",
            "eval_024_numeric_speakers": "Tests numeric-only speaker identifiers.",
            "eval_025_special_characters_in_names": "Tests special characters in names.",
        }
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MeetMind Claude Evaluation Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        
        /* Header */
        .header {{
            background: white;
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-label {{ color: #666; margin-top: 8px; }}
        
        /* Test Card */
        .test-card {{
            background: white;
            border-radius: 12px;
            margin-bottom: 25px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .test-header {{
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .test-passed {{ background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); }}
        .test-failed {{ background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); }}
        .test-warning {{ background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); }}
        
        .test-id {{ font-size: 1.2em; font-weight: bold; }}
        .test-score {{
            font-size: 1.1em;
            font-weight: bold;
            padding: 5px 15px;
            border-radius: 20px;
            background: rgba(0,0,0,0.1);
        }}
        
        .test-purpose {{
            padding: 15px 20px;
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            margin: 0;
        }}
        
        .validation-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 10px;
            padding: 20px;
            background: #f8f9fa;
        }}
        .validation-item {{
            padding: 10px;
            border-radius: 6px;
            font-size: 0.9em;
        }}
        .validation-pass {{
            background: #d4edda;
            border-left: 3px solid #28a745;
        }}
        .validation-fail {{
            background: #f8d7da;
            border-left: 3px solid #dc3545;
        }}
        
        .output-section {{
            padding: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        .output-title {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #667eea;
        }}
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 0.85em;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 MeetMind Claude Evaluation Report</h1>
            <p>Generated: {timestamp}</p>
            <p>Model: {summary.model}</p>
            <p><em>Using semantic keyword matching (synonyms + stemming)</em></p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{summary.overall_score:.1f}%</div>
                <div class="stat-label">Overall Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.weighted_score:.1f}%</div>
                <div class="stat-label">Weighted Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.passed_tests}/{summary.total_tests}</div>
                <div class="stat-label">Tests Passed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.passed_checks}/{summary.total_checks}</div>
                <div class="stat-label">Checks Passed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.avg_latency_seconds:.1f}s</div>
                <div class="stat-label">Avg Latency</div>
            </div>
        </div>
"""
        
        for result in summary.results:
            # Determine card style
            if result.score >= 90:
                card_class = "test-passed"
            elif result.score >= 70:
                card_class = "test-warning"
            else:
                card_class = "test-failed"
            
            html += f"""
        <div class="test-card">
            <div class="test-header {card_class}">
                <div class="test-id">
                    {result.id}
                    <span style="font-size: 0.85em; color: #666;">{result.description}</span>
                </div>
                <div class="test-score">Score: {result.score:.1f}% ({result.passed_checks}/{result.total_checks}) | {result.latency_seconds}s</div>
            </div>
            
            <div class="test-purpose">
                <strong>🎯 Test Purpose:</strong> {test_purposes.get(result.id, 'Tests Claude meeting extraction capabilities.')}
            </div>
            
            <div class="validation-grid">
"""
            
            for validation in result.validations:
                status_class = "validation-pass" if validation.passed else "validation-fail"
                icon = "✅" if validation.passed else "❌"
                html += f"""
                <div class="validation-item {status_class}">
                    <strong>{icon} {validation.name}</strong><br>
                    Expected: {validation.expected}<br>
                    Actual: {validation.actual}<br>
                    <span style="font-size: 0.85em;">{validation.message}</span>
                </div>
"""
            
            html += """
            </div>
            
            <div class="output-section">
                <div class="output-title">📝 Claude's Summary</div>
                <pre style="white-space: pre-wrap;">""" + result.claude_output.get('summary', 'N/A')[:500] + """</pre>
            </div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    @staticmethod
    def generate_json(summary: EvaluationSummary) -> str:
        """Generate JSON report"""
        return json.dumps({
            "timestamp": summary.timestamp,
            "model": summary.model,
            "overall_score": summary.overall_score,
            "weighted_score": summary.weighted_score,
            "total_tests": summary.total_tests,
            "passed_tests": summary.passed_tests,
            "failed_tests": summary.failed_tests,
            "total_checks": summary.total_checks,
            "passed_checks": summary.passed_checks,
            "avg_latency_seconds": summary.avg_latency_seconds,
            "semantic_matching_enabled": True,
            "results": [r.to_dict() for r in summary.results]
        }, indent=2)


# ============================================================================
# Main Evaluation Runner
# ============================================================================

class EvaluationRunner:
    """Main evaluation runner with rate limiting and caching"""
    
    def __init__(self, rate_limit_seconds: float = 0.5):
        self.rate_limit = rate_limit_seconds
        self.engine = EvaluationEngine()
        self.report_gen = ReportGenerator()
        self.cache = {}  # Simple cache for transcripts
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load test cases from golden dataset"""
        path = Path(__file__).parent / "golden_dataset.json"
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        # Add default severity if not present
        for case in dataset:
            if 'severity' not in case:
                case['severity'] = 'medium'
        
        return dataset
    
    def get_transcript_hash(self, transcript: str) -> str:
        """Generate hash for transcript caching"""
        return hashlib.md5(transcript.encode()).hexdigest()
    
    async def run(self) -> EvaluationSummary:
        """Run complete evaluation"""
        
        print(f"\n{'='*80}")
        print(f"MeetMind Claude Evaluation System")
        print(f"{'='*80}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Model: {settings.claude_model}")
        print(f"Semantic Matching: ENABLED (synonyms + stemming)")
        print(f"{'='*80}\n")
        
        # Load dataset
        dataset = self.load_dataset()
        print(f"📋 Loaded {len(dataset)} test cases\n")
        
        # Run evaluations
        results = []
        total_latency = 0
        
        for i, case in enumerate(dataset, 1):
            print(f"[{i}/{len(dataset)}] Running: {case['id']}")
            print(f"  Description: {case.get('description', '')}")
            
            result = await self.engine.evaluate_case(
                case,
                case["transcript"],
                case["expected"]
            )
            
            results.append(result)
            total_latency += result.latency_seconds
            
            # Show status
            status_icon = "✅" if result.passed else "❌"
            print(f"  {status_icon} Score: {result.score:.1f}% ({result.passed_checks}/{result.total_checks}) - {result.latency_seconds}s")
            
            if result.error:
                print(f"  ⚠️ Error: {result.error[:100]}")
            
            if result.validations:
                failed = [v for v in result.validations if not v.passed]
                if failed:
                    print(f"  ❌ Failed: {', '.join([v.name for v in failed])}")
            
            print()
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit)
        
        # Calculate summary
        summary = EvaluationSummary(
            timestamp=datetime.now().isoformat(),
            model=settings.claude_model,
            total_tests=len(results),
            passed_tests=sum(1 for r in results if r.passed),
            failed_tests=sum(1 for r in results if not r.passed),
            overall_score=sum(r.score for r in results) / len(results) if results else 0,
            total_checks=sum(r.total_checks for r in results),
            passed_checks=sum(r.passed_checks for r in results),
            avg_latency_seconds=total_latency / len(results) if results else 0,
            results=results
        )
        
        # Print summary
        print(f"{'='*80}")
        print(f"EVALUATION COMPLETE")
        print(f"{'='*80}")
        print(f"Overall Score: {summary.overall_score:.1f}%")
        print(f"Weighted Score: {summary.weighted_score:.1f}%")
        print(f"Tests Passed: {summary.passed_tests}/{summary.total_tests}")
        print(f"Checks Passed: {summary.passed_checks}/{summary.total_checks}")
        print(f"Avg Latency: {summary.avg_latency_seconds:.2f}s")
        print(f"Semantic Matching: Enabled (reducing false failures)")
        print(f"{'='*80}\n")
        
        # Save reports
        output_dir = Path(__file__).parent / "results"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON report
        json_content = self.report_gen.generate_json(summary)
        json_file = output_dir / f"eval_report_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
        print(f"📊 JSON report: {json_file}")
        
        # HTML report
        html_content = self.report_gen.generate_html(summary)
        html_file = output_dir / f"eval_report_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📊 HTML report: {html_file}")
        
        # Try to open in VS Code
        try:
            import subprocess
            subprocess.run(['code', '--reuse-window', str(html_file)], 
                          capture_output=True, check=False)
            print(f"📂 Opened in VS Code")
        except:
            print(f"💡 Open manually: {html_file}")
        
        return summary


# ============================================================================
# Entry Point
# ============================================================================

async def main():
    """Main entry point"""
    runner = EvaluationRunner(rate_limit_seconds=0.5)
    summary = await runner.run()
    
    # Exit with appropriate code
    exit_code = 0 if summary.overall_score >= 80 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())