from app.site_intelligence import _extract_result_url, _host, _relevance


def test_host_normalizes_www_and_case():
    assert _host("https://WWW.Example.com/path") == "example.com"


def test_same_category_gets_higher_relevance():
    same, same_reason = _relevance("SaaS / Web App", "Workflow platform", "tools for teams", "SaaS / Web App")
    different, _ = _relevance("SaaS / Web App", "Cooking recipes", "food and recipes", "Blog / Publication")
    assert same > different
    assert "same website category" in same_reason


def test_relevance_score_is_bounded():
    score, reason = _relevance("E-commerce", "E-commerce platform alternatives", "software tool", "E-commerce")
    assert 0 <= score <= 100
    assert reason


def test_extract_result_url_accepts_direct_https_url():
    assert _extract_result_url("https://example.com/products") == "https://example.com/products"


def test_extract_result_url_resolves_duckduckgo_redirect():
    href = "/l/?uddg=https%3A%2F%2Fexample.com%2Fproducts%3Fref%3Dsearch&rut=ignored"
    assert _extract_result_url(href) == "https://example.com/products?ref=search"


def test_extract_result_url_rejects_unresolvable_or_non_web_links():
    assert _extract_result_url("/l/?rut=missing-destination") == ""
    assert _extract_result_url("javascript:alert(1)") == ""
    assert _extract_result_url("https://duckduckgo.com/about") == ""
