import re

# Common synonyms so keyword matching doesn't fail on minor wording differences
# e.g. Claude writes "defer" but the dataset expects "table"
SYNONYMS: dict[str, list[str]] = {
    "table":      ["table", "defer", "postpone", "delay", "put off", "hold"],
    "defer":      ["defer", "postpone", "delay", "table", "put off", "hold"],
    "block":      ["block", "blocking", "blocked", "blocker", "stuck", "prevent"],
    "deploy":     ["deploy", "deployed", "deploying", "deployment", "release", "ship"],
    "migrate":    ["migrat", "migrate", "migrated", "migrating", "migration", "move"],
    "optimize":   ["optimiz", "optimize", "optimized", "optimization", "improve", "tune"],
    "database":   ["database", "db", "data store", "sql"],
    "staging":    ["staging", "test", "sandbox", "development", "dev"],
    "payment":    ["payment", "payments", "transaction", "billing", "charge"],
    "api":        ["api", "endpoint", "service", "interface"],
    "aws":        ["aws", "amazon web services", "amazon"],
    "postgresql": ["postgresql", "postgres", "pg"],
    "kubernetes": ["kubernetes", "k8s", "kube"],
    "ssl":        ["ssl", "certificate", "tls", "cert", "encryption"],
    "wiki":       ["wiki", "documentation", "docs", "knowledge base", "confluence"],
    "document": ["document", "doc", "documentation", "write up", "known issues doc"],
}


def _stem(word: str) -> str:
    # simple suffix stripping — good enough for English eval keywords
    for suffix in ("ing", "ed", "tion", "ize", "ise", "able", "ible", "er", "es", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            return word[:-len(suffix)]
    return word


def keyword_found(keyword: str, text: str) -> bool:
    text = re.sub(r"[^\w\s]", "", text.lower())
    kw   = keyword.lower()

    if kw in text:
        return True

    for synonym in SYNONYMS.get(kw, []):
        if synonym in text:
            return True

    stemmed_kw = _stem(kw)
    return any(_stem(w) == stemmed_kw for w in text.split())