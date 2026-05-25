# pytest tests/test_eval.py -v
from eval.keywords import keyword_found
from eval.checks import check_count


class TestKeywordFound:

    def test_exact_match(self):
        assert keyword_found("stripe", "Stripe sandbox is down") is True

    def test_case_insensitive(self):
        assert keyword_found("Stripe", "stripe is down") is True

    def test_synonym_match(self):
        # "table" should match "defer" via synonyms
        assert keyword_found("table", "let's defer this to next week") is True

    def test_stemmed_match(self):
        # "deploy" should match "deploying"
        assert keyword_found("deploy", "we are deploying on Friday") is True

    def test_no_match(self):
        assert keyword_found("stripe", "we use PayPal for payments") is False

    def test_empty_text(self):
        assert keyword_found("stripe", "") is False


class TestCheckCount:

    def test_exact_match_passes(self):
        checks = check_count("action_items", 2, {"action_items_exact": 2})
        assert checks[0].passed is True

    def test_exact_match_fails(self):
        checks = check_count("action_items", 3, {"action_items_exact": 2})
        assert checks[0].passed is False

    def test_exact_overrides_min_max(self):
        # exact should return early, ignoring min/max
        checks = check_count("action_items", 2, {
            "action_items_exact": 2,
            "action_items_min": 5,   # would fail if reached
        })
        assert len(checks) == 1
        assert checks[0].passed is True

    def test_min_passes(self):
        checks = check_count("action_items", 3, {"action_items_min": 2})
        assert checks[0].passed is True

    def test_min_fails(self):
        checks = check_count("action_items", 1, {"action_items_min": 2})
        assert checks[0].passed is False

    def test_max_passes(self):
        checks = check_count("action_items", 2, {"action_items_max": 3})
        assert checks[0].passed is True

    def test_max_fails(self):
        checks = check_count("action_items", 4, {"action_items_max": 3})
        assert checks[0].passed is False

    def test_min_zero_no_max_enforces_zero(self):
        # min=0 with no max means exactly zero expected
        checks = check_count("decisions", 2, {"decisions_min": 0})
        names = [c.name for c in checks]
        assert "decisions_zero_enforced" in names
        zero_check = next(c for c in checks if c.name == "decisions_zero_enforced")
        assert zero_check.passed is False

    def test_min_zero_with_actual_zero_passes(self):
        checks = check_count("decisions", 0, {"decisions_min": 0})
        assert all(c.passed for c in checks)

    def test_min_zero_with_max_allows_items(self):
        # min=0 AND max=3 means 0-3 is fine — zero_enforced should NOT appear
        checks = check_count("decisions", 2, {"decisions_min": 0, "decisions_max": 3})
        names = [c.name for c in checks]
        assert "decisions_zero_enforced" not in names