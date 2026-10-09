import json

from app.ai import _audit_context, _parse_ai_response, generate_ai_backlog


def sample_audit():
    return {
        "url": "https://shop.example/",
        "website_type": "E-commerce",
        "score_status": "verified",
        "verified_pages": 4,
        "unverified_pages": 1,
        "features": {"sector_signals": {"commerce": True}},
        "issues": [{
            "title": "Missing product description",
            "severity": "medium",
            "page_url": "https://shop.example/item",
            "evidence": "Product page description was empty.",
            "impact": "Customers and search engines get less product context.",
            "recommendation": "Write a useful, unique product description.",
            "priority": 62,
        }],
        "opportunities": [{
            "title": "Validate the product-to-checkout journey",
            "reason": "Commerce-related page signals were observed; checkout was not verified.",
            "action": "Manually test product details, cart, checkout, shipping and error states.",
        }],
    }


def test_ai_fallback_includes_verified_findings_and_sector_opportunities(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)

    result = generate_ai_backlog(sample_audit())

    assert result["mode"] == "deterministic"
    assert result["items"][0]["basis_title"] == "Missing product description"
    assert any(x["source"] == "sector_opportunity" for x in result["items"])
    assert all("priority" in x and "action" in x for x in result["items"])


def test_ai_response_accepts_json_grounded_in_a_finding():
    context = _audit_context(sample_audit())
    content = json.dumps({
        "summary": "Prioritize the observed product detail issue.",
        "items": [{
            "title": "Improve product detail clarity",
            "why": "The sampled product page has an empty description.",
            "action": "Add a unique and accurate product description.",
            "priority": 62,
            "source": "observed_finding",
            "basis_title": "Missing product description",
        }],
    })

    result = _parse_ai_response(content, context)

    assert result is not None
    assert result["mode"] == "llm"
    assert result["items"][0]["basis_title"] == "Missing product description"


def test_ai_response_accepts_fenced_json():
    context = _audit_context(sample_audit())
    payload = {
        "summary": "Review the product flow.",
        "items": [{
            "title": "Test checkout",
            "why": "The public crawl did not verify checkout.",
            "action": "Manually test the full purchase journey.",
            "priority": 55,
            "source": "sector_opportunity",
            "basis_title": "Validate the product-to-checkout journey",
        }],
    }

    result = _parse_ai_response("```json\n" + json.dumps(payload) + "\n```", context)

    assert result is not None
    assert result["items"][0]["source"] == "sector_opportunity"


def test_ai_response_rejects_invented_basis_title():
    context = _audit_context(sample_audit())
    content = json.dumps({
        "summary": "The store is underperforming.",
        "items": [{
            "title": "Fix low conversion",
            "why": "Conversion is low.",
            "action": "Change the checkout.",
            "priority": 90,
            "source": "observed_finding",
            "basis_title": "Low conversion rate",
        }],
    })

    assert _parse_ai_response(content, context) is None


def test_ai_response_rejects_invalid_priority_and_non_json():
    context = _audit_context(sample_audit())
    payload = {
        "summary": "Summary",
        "items": [{
            "title": "Fix description",
            "why": "Observed issue.",
            "action": "Write the description.",
            "priority": 999,
            "source": "observed_finding",
            "basis_title": "Missing product description",
        }],
    }

    assert _parse_ai_response(json.dumps(payload), context) is None
    assert _parse_ai_response("not json", context) is None


def test_provider_failure_uses_fallback_without_exposing_exception_text(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_BASE_URL", "https://provider.example/v1")

    def fail_request(*args, **kwargs):
        raise RuntimeError("secret request details")

    monkeypatch.setattr("app.ai.httpx.post", fail_request)
    result = generate_ai_backlog(sample_audit())

    assert result["mode"] == "fallback"
    assert result["items"]
    assert "secret request details" not in result["error"]
