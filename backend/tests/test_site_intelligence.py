from types import SimpleNamespace

from app.site_intelligence import _extract_result_url, _host, _parse_duckduckgo_results, _relevance, discover_similar


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


def test_parse_duckduckgo_standard_result_markup():
    html = """
    <div class="result">
      <a class="result__a" href="https://example.com/tools">Example Tools</a>
      <a class="result__snippet">Tools for turning text into visuals</a>
    </div>
    """
    results = _parse_duckduckgo_results(html, 5)
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/tools"
    assert results[0]["name"] == "Example Tools"


def test_parse_duckduckgo_lite_result_markup():
    html = """
    <table><tr><td><a class="result-link" href="https://example.org/">Example Org</a></td></tr></table>
    """
    results = _parse_duckduckgo_results(html, 5, "DuckDuckGo Lite")
    assert len(results) == 1
    assert results[0]["source"] == "DuckDuckGo Lite"


def test_parse_duckduckgo_results_deduplicates_urls():
    html = """
    <a class="result__a" href="https://example.com/">Example</a>
    <a class="result__a" href="https://example.com/">Example duplicate</a>
    """
    results = _parse_duckduckgo_results(html, 5)
    assert len(results) == 1


def test_curated_references_do_not_publish_fake_similarity_percentages(monkeypatch):
    monkeypatch.setattr("app.site_intelligence._search", lambda query, limit=8: [])
    target = SimpleNamespace(root_url="https://www.youtube.com/", pages=[])
    results = discover_similar(target, "Video / Media Platform")

    assert {item["name"] for item in results} >= {"Vimeo", "Dailymotion", "Twitch"}
    assert all(item["relevance_score"] is None for item in results)
    assert all(item["verification_status"] == "curated-reference" for item in results)
    assert next(item for item in results if item["name"] == "Twitch")["match_type"] == "Adjacent alternative"
    assert all(item["match_type"] == "Category reference" for item in results if item["name"] != "Twitch")
