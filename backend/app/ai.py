from .analyzers import Finding


def build_ai_context(findings: list[Finding]) -> list[dict[str, str]]:
    """Return structured findings ready for an LLM recommendation layer.

    The initial implementation intentionally does not call an external model.
    Keeping detection deterministic makes the audit engine testable and lets
    the AI layer focus on explanation and prioritization later.
    """
    return [
        {
            "category": item.category,
            "title": item.title,
            "severity": item.severity,
            "impact": item.impact,
            "recommendation": item.recommendation,
        }
        for item in findings
    ]
